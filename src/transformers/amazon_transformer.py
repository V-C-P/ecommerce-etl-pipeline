from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AmazonTransformer:
    """Transform Amazon SP-API data to match our database schema"""

    @staticmethod
    def transform_customer(amazon_order: Dict) -> Dict:
        """
        Transform Amazon order data to customer format
        Note: Amazon doesn't provide detailed customer info, so we extract what we can from orders

        Args:
            amazon_order: Raw Amazon order data

        Returns:
            Transformed customer dictionary
        """
        buyer_info = amazon_order.get('BuyerInfo', {}) or {}

        return {
            'external_id': amazon_order.get('AmazonOrderId'),  # Use order ID as customer ID
            'platform': 'amazon',
            'email': buyer_info.get('BuyerEmail'),
            'first_name': None,  # Amazon doesn't provide this
            'last_name': None,   # Amazon doesn't provide this
            'phone': None,       # Amazon doesn't provide this
            'total_orders': 1,   # We can't get total orders from Amazon API easily
            'total_spent': float(amazon_order.get('OrderTotal', {}).get('Amount', 0)),
            'created_at': amazon_order.get('PurchaseDate'),
            'updated_at': amazon_order.get('LastUpdateDate')
        }

    @staticmethod
    def transform_product(amazon_item: Dict) -> Dict:
        """
        Transform Amazon order item to product format

        Args:
            amazon_item: Raw Amazon order item data

        Returns:
            Transformed product dictionary
        """
        return {
            'external_id': amazon_item.get('ASIN'),
            'platform': 'amazon',
            'sku': amazon_item.get('SellerSKU'),
            'title': amazon_item.get('Title'),
            'description': None,  # Not available in order items API
            'vendor': None,       # Not available
            'product_type': None, # Not available
            'price': float(amazon_item.get('ItemPrice', {}).get('Amount', 0)),
            'inventory_quantity': None,  # Not available in orders API
            'image_url': None,    # Not available in orders API
            'created_at': None,
            'updated_at': None
        }

    @staticmethod
    def transform_order(amazon_order: Dict) -> Dict:
        """
        Transform Amazon order to database format

        Args:
            amazon_order: Raw Amazon order data

        Returns:
            Transformed order dictionary
        """
        # Extract shipping address if available
        shipping_address = amazon_order.get('ShippingAddress', {}) or {}

        # Calculate totals
        order_total = amazon_order.get('OrderTotal', {}) or {}
        total_price = float(order_total.get('Amount', 0))

        # Amazon provides different pricing structure
        # We'll approximate based on available data
        buyer_info = amazon_order.get('BuyerInfo', {}) or {}

        return {
            'external_id': amazon_order.get('AmazonOrderId'),
            'platform': 'amazon',
            'order_number': amazon_order.get('AmazonOrderId'),  # Amazon uses same ID
            'customer_external_id': amazon_order.get('AmazonOrderId'),  # Use order ID as customer reference
            'email': buyer_info.get('BuyerEmail'),

            # Financial info
            'total_price': total_price,
            'subtotal_price': total_price,  # Amazon doesn't break this down easily
            'total_tax': 0,  # Would need to sum from items
            'total_discounts': 0,  # Would need to calculate from items
            'total_shipping': 0,  # Would need to sum from items
            'currency': order_total.get('CurrencyCode'),

            # Status - Amazon uses different status values
            'financial_status': AmazonTransformer._map_payment_status(amazon_order.get('OrderStatus')),
            'fulfillment_status': AmazonTransformer._map_fulfillment_status(amazon_order.get('FulfillmentChannel'), amazon_order.get('OrderStatus')),
            'order_status': AmazonTransformer._map_order_status(amazon_order.get('OrderStatus')),

            # Shipping info
            'shipping_name': shipping_address.get('Name'),
            'shipping_address_1': shipping_address.get('AddressLine1'),
            'shipping_address_2': shipping_address.get('AddressLine2'),
            'shipping_city': shipping_address.get('City'),
            'shipping_province': shipping_address.get('StateOrRegion'),
            'shipping_country': shipping_address.get('CountryCode'),
            'shipping_zip': shipping_address.get('PostalCode'),

            # Dates
            'order_date': amazon_order.get('PurchaseDate'),
            'processed_at': amazon_order.get('PurchaseDate'),
            'cancelled_at': None,  # Would need to check if OrderStatus is Cancelled
            'created_at': amazon_order.get('PurchaseDate'),
            'updated_at': amazon_order.get('LastUpdateDate')
        }

    @staticmethod
    def transform_line_item(amazon_item: Dict, order_external_id: str) -> Dict:
        """
        Transform Amazon order item to database format

        Args:
            amazon_item: Raw Amazon order item data
            order_external_id: External ID of the parent order

        Returns:
            Transformed line item dictionary
        """
        item_price = amazon_item.get('ItemPrice', {}) or {}
        item_tax = amazon_item.get('ItemTax', {}) or {}
        promotion_discount = amazon_item.get('PromotionDiscount', {}) or {}

        return {
            'external_id': amazon_item.get('OrderItemId'),
            'order_external_id': order_external_id,
            'product_external_id': amazon_item.get('ASIN'),
            'sku': amazon_item.get('SellerSKU'),
            'title': amazon_item.get('Title'),
            'variant_title': None,  # Amazon doesn't have variants in the same way
            'quantity': int(amazon_item.get('QuantityOrdered', 1)),
            'price': float(item_price.get('Amount', 0)) / int(amazon_item.get('QuantityOrdered', 1)),
            'total_discount': float(promotion_discount.get('Amount', 0)),
            'tax': float(item_tax.get('Amount', 0)),
            'fulfillment_status': None,  # Not provided at item level
            'requires_shipping': True  # Assume true for Amazon orders
        }

    @staticmethod
    def _map_payment_status(amazon_status: str) -> str:
        """Map Amazon order status to our financial_status"""
        status_map = {
            'Pending': 'pending',
            'Unshipped': 'paid',
            'PartiallyShipped': 'paid',
            'Shipped': 'paid',
            'Canceled': 'voided',
            'Unfulfillable': 'pending'
        }
        return status_map.get(amazon_status, 'pending')

    @staticmethod
    def _map_fulfillment_status(fulfillment_channel: str, order_status: str) -> Optional[str]:
        """Map Amazon fulfillment info to our fulfillment_status"""
        if order_status == 'Shipped':
            return 'fulfilled'
        elif order_status == 'PartiallyShipped':
            return 'partial'
        elif order_status in ['Unshipped', 'Pending']:
            return 'unfulfilled'
        return None

    @staticmethod
    def _map_order_status(amazon_status: str) -> str:
        """Map Amazon order status to our order_status"""
        if amazon_status == 'Canceled':
            return 'cancelled'
        elif amazon_status == 'Shipped':
            return 'closed'
        else:
            return 'open'

    @staticmethod
    def transform_order_with_details(amazon_order: Dict) -> Dict:
        """
        Transform a complete Amazon order with all related data

        Args:
            amazon_order: Raw Amazon order data with OrderItems

        Returns:
            Dictionary with transformed order and line_items
        """
        order = AmazonTransformer.transform_order(amazon_order)
        order_external_id = order['external_id']

        # Transform line items
        line_items = [
            AmazonTransformer.transform_line_item(item, order_external_id)
            for item in amazon_order.get('OrderItems', [])
        ]

        # Extract unique products from line items
        products = []
        seen_asins = set()
        for item in amazon_order.get('OrderItems', []):
            asin = item.get('ASIN')
            if asin and asin not in seen_asins:
                products.append(AmazonTransformer.transform_product(item))
                seen_asins.add(asin)

        return {
            'order': order,
            'line_items': line_items,
            'products': products,
            'customer': AmazonTransformer.transform_customer(amazon_order)
        }
