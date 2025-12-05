from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ShopifyTransformer:
    """Transform Shopify data to match our database schema"""

    @staticmethod
    def transform_customer(shopify_customer: Dict) -> Dict:
        """
        Transform Shopify customer to database format

        Args:
            shopify_customer: Raw Shopify customer data

        Returns:
            Transformed customer dictionary
        """
        return {
            'external_id': str(shopify_customer.get('id')),
            'platform': 'shopify',
            'email': shopify_customer.get('email'),
            'first_name': shopify_customer.get('first_name'),
            'last_name': shopify_customer.get('last_name'),
            'phone': shopify_customer.get('phone'),
            'total_orders': shopify_customer.get('orders_count', 0),
            'total_spent': float(shopify_customer.get('total_spent', 0)),
            'created_at': shopify_customer.get('created_at'),
            'updated_at': shopify_customer.get('updated_at')
        }

    @staticmethod
    def transform_product(shopify_product: Dict, variant: Optional[Dict] = None) -> Dict:
        """
        Transform Shopify product to database format

        Args:
            shopify_product: Raw Shopify product data
            variant: Specific variant data (if handling variants separately)

        Returns:
            Transformed product dictionary
        """
        # If variant is provided, use variant-specific data
        if variant:
            external_id = str(variant.get('id'))
            sku = variant.get('sku')
            price = float(variant.get('price', 0))
            inventory = variant.get('inventory_quantity', 0)
            title = f"{shopify_product.get('title')} - {variant.get('title')}"
        else:
            # Use first variant or product-level data
            variants = shopify_product.get('variants', [])
            first_variant = variants[0] if variants else {}

            external_id = str(shopify_product.get('id'))
            sku = first_variant.get('sku')
            price = float(first_variant.get('price', 0))
            inventory = first_variant.get('inventory_quantity', 0)
            title = shopify_product.get('title')

        # Get first image URL
        images = shopify_product.get('images', [])
        image_url = images[0].get('src') if images else None

        return {
            'external_id': external_id,
            'platform': 'shopify',
            'sku': sku,
            'title': title,
            'description': shopify_product.get('body_html'),
            'vendor': shopify_product.get('vendor'),
            'product_type': shopify_product.get('product_type'),
            'price': price,
            'inventory_quantity': inventory,
            'image_url': image_url,
            'created_at': shopify_product.get('created_at'),
            'updated_at': shopify_product.get('updated_at')
        }

    @staticmethod
    def transform_order(shopify_order: Dict) -> Dict:
        """
        Transform Shopify order to database format

        Args:
            shopify_order: Raw Shopify order data

        Returns:
            Transformed order dictionary
        """
        # Extract shipping address
        shipping_address = shopify_order.get('shipping_address', {}) or {}

        # Get customer info
        customer = shopify_order.get('customer', {}) or {}

        return {
            'external_id': str(shopify_order.get('id')),
            'platform': 'shopify',
            'order_number': shopify_order.get('order_number'),
            'customer_external_id': str(customer.get('id')) if customer.get('id') else None,
            'email': shopify_order.get('email') or customer.get('email'),

            # Financial info
            'total_price': float(shopify_order.get('total_price', 0)),
            'subtotal_price': float(shopify_order.get('subtotal_price', 0)),
            'total_tax': float(shopify_order.get('total_tax', 0)),
            'total_discounts': float(shopify_order.get('total_discounts', 0)),
            'total_shipping': float(shopify_order.get('total_shipping_price_set', {}).get('shop_money', {}).get('amount', 0)),
            'currency': shopify_order.get('currency'),

            # Status
            'financial_status': shopify_order.get('financial_status'),
            'fulfillment_status': shopify_order.get('fulfillment_status'),
            'order_status': 'cancelled' if shopify_order.get('cancelled_at') else ('closed' if shopify_order.get('closed_at') else 'open'),

            # Shipping info
            'shipping_name': shipping_address.get('name'),
            'shipping_address_1': shipping_address.get('address1'),
            'shipping_address_2': shipping_address.get('address2'),
            'shipping_city': shipping_address.get('city'),
            'shipping_province': shipping_address.get('province'),
            'shipping_country': shipping_address.get('country'),
            'shipping_zip': shipping_address.get('zip'),

            # Dates
            'order_date': shopify_order.get('created_at'),
            'processed_at': shopify_order.get('processed_at'),
            'cancelled_at': shopify_order.get('cancelled_at'),
            'created_at': shopify_order.get('created_at'),
            'updated_at': shopify_order.get('updated_at')
        }

    @staticmethod
    def transform_line_item(line_item: Dict, order_external_id: str) -> Dict:
        """
        Transform Shopify line item to database format

        Args:
            line_item: Raw Shopify line item data
            order_external_id: External ID of the parent order

        Returns:
            Transformed line item dictionary
        """
        return {
            'external_id': str(line_item.get('id')),
            'order_external_id': order_external_id,
            'product_external_id': str(line_item.get('product_id')) if line_item.get('product_id') else None,
            'sku': line_item.get('sku'),
            'title': line_item.get('title'),
            'variant_title': line_item.get('variant_title'),
            'quantity': line_item.get('quantity', 1),
            'price': float(line_item.get('price', 0)),
            'total_discount': float(line_item.get('total_discount', 0)),
            'tax': sum([float(tax.get('price', 0)) for tax in line_item.get('tax_lines', [])]),
            'fulfillment_status': line_item.get('fulfillment_status'),
            'requires_shipping': line_item.get('requires_shipping', True)
        }

    @staticmethod
    def transform_fulfillment(fulfillment: Dict, order_external_id: str) -> Dict:
        """
        Transform Shopify fulfillment to database format

        Args:
            fulfillment: Raw Shopify fulfillment data
            order_external_id: External ID of the parent order

        Returns:
            Transformed fulfillment dictionary
        """
        return {
            'external_id': str(fulfillment.get('id')),
            'order_external_id': order_external_id,
            'platform': 'shopify',
            'status': fulfillment.get('status'),
            'tracking_company': fulfillment.get('tracking_company'),
            'tracking_number': fulfillment.get('tracking_number'),
            'tracking_url': fulfillment.get('tracking_url'),
            'shipped_at': fulfillment.get('created_at'),
            'created_at': fulfillment.get('created_at'),
            'updated_at': fulfillment.get('updated_at')
        }

    @staticmethod
    def transform_order_with_details(shopify_order: Dict) -> Dict:
        """
        Transform a complete Shopify order with all related data

        Args:
            shopify_order: Raw Shopify order data

        Returns:
            Dictionary with transformed order, line_items, and fulfillments
        """
        order = ShopifyTransformer.transform_order(shopify_order)
        order_external_id = order['external_id']

        # Transform line items
        line_items = [
            ShopifyTransformer.transform_line_item(item, order_external_id)
            for item in shopify_order.get('line_items', [])
        ]

        # Transform fulfillments
        fulfillments = [
            ShopifyTransformer.transform_fulfillment(fulfillment, order_external_id)
            for fulfillment in shopify_order.get('fulfillments', [])
        ]

        return {
            'order': order,
            'line_items': line_items,
            'fulfillments': fulfillments
        }
