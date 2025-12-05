from sp_api.api import Orders, Products, Reports
from sp_api.base import Marketplaces, SellingApiException
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class AmazonExtractor:
    """Extract data from Amazon SP-API"""

    def __init__(self, refresh_token: str, client_id: str, client_secret: str,
                 marketplace: str = 'US'):
        """
        Initialize Amazon SP-API client

        Args:
            refresh_token: Amazon SP-API refresh token
            client_id: LWA client identifier
            client_secret: LWA client secret
            marketplace: Marketplace code (default: 'US')
        """
        self.credentials = {
            'refresh_token': refresh_token,
            'lwa_app_id': client_id,
            'lwa_client_secret': client_secret
        }

        # Map marketplace codes to SP-API Marketplace objects
        marketplace_map = {
            'US': Marketplaces.US,
            'CA': Marketplaces.CA,
            'MX': Marketplaces.MX,
            'UK': Marketplaces.UK,
            'DE': Marketplaces.DE,
            'FR': Marketplaces.FR,
            'IT': Marketplaces.IT,
            'ES': Marketplaces.ES,
            'JP': Marketplaces.JP,
            'AU': Marketplaces.AU
        }

        self.marketplace = marketplace_map.get(marketplace, Marketplaces.US)

        # Initialize API clients
        self.orders_api = None
        self.products_api = None
        self.reports_api = None

        logger.info(f"Initialized Amazon SP-API for marketplace: {marketplace}")

    def _get_orders_api(self) -> Orders:
        """Get or create Orders API client"""
        if not self.orders_api:
            self.orders_api = Orders(
                credentials=self.credentials,
                marketplace=self.marketplace
            )
        return self.orders_api

    def _get_products_api(self) -> Products:
        """Get or create Products API client"""
        if not self.products_api:
            self.products_api = Products(
                credentials=self.credentials,
                marketplace=self.marketplace
            )
        return self.products_api

    def extract_orders(self, days_back: int = 7) -> List[Dict]:
        """
        Extract orders from Amazon

        Args:
            days_back: Number of days to look back

        Returns:
            List of order dictionaries
        """
        logger.info(f"Extracting Amazon orders from last {days_back} days")

        created_after = (datetime.utcnow() - timedelta(days=days_back)).isoformat()

        all_orders = []

        try:
            orders_api = self._get_orders_api()

            # Get orders
            response = orders_api.get_orders(
                CreatedAfter=created_after,
                MarketplaceIds=[self.marketplace.marketplace_id]
            )

            orders = response.payload.get('Orders', [])
            all_orders.extend(orders)

            logger.info(f"Fetched {len(orders)} orders from Amazon")

            # Handle pagination
            next_token = response.payload.get('NextToken')
            while next_token:
                logger.info("Fetching next page of Amazon orders...")
                response = orders_api.get_orders(
                    NextToken=next_token
                )
                orders = response.payload.get('Orders', [])
                all_orders.extend(orders)
                logger.info(f"Fetched {len(orders)} more orders, total: {len(all_orders)}")
                next_token = response.payload.get('NextToken')

        except SellingApiException as e:
            logger.error(f"Amazon SP-API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error extracting Amazon orders: {e}")
            raise

        logger.info(f"Total Amazon orders extracted: {len(all_orders)}")
        return all_orders

    def extract_order_items(self, order_id: str) -> List[Dict]:
        """
        Extract line items for a specific order

        Args:
            order_id: Amazon order ID

        Returns:
            List of order item dictionaries
        """
        logger.info(f"Extracting items for Amazon order {order_id}")

        all_items = []

        try:
            orders_api = self._get_orders_api()

            response = orders_api.get_order_items(order_id)
            items = response.payload.get('OrderItems', [])
            all_items.extend(items)

            # Handle pagination
            next_token = response.payload.get('NextToken')
            while next_token:
                response = orders_api.get_order_items(
                    order_id,
                    NextToken=next_token
                )
                items = response.payload.get('OrderItems', [])
                all_items.extend(items)
                next_token = response.payload.get('NextToken')

        except SellingApiException as e:
            logger.error(f"Amazon SP-API error getting order items: {e}")
            raise
        except Exception as e:
            logger.error(f"Error extracting Amazon order items: {e}")
            raise

        logger.info(f"Extracted {len(all_items)} items for order {order_id}")
        return all_items

    def extract_order_address(self, order_id: str) -> Optional[Dict]:
        """
        Extract shipping address for a specific order

        Args:
            order_id: Amazon order ID

        Returns:
            Address dictionary or None
        """
        try:
            orders_api = self._get_orders_api()
            response = orders_api.get_order_address(order_id)
            return response.payload.get('ShippingAddress')
        except SellingApiException as e:
            logger.warning(f"Could not get address for order {order_id}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error getting order address: {e}")
            return None

    def extract_orders_with_details(self, days_back: int = 7) -> List[Dict]:
        """
        Extract orders with all related details (items, address)

        Args:
            days_back: Number of days to look back

        Returns:
            List of enriched order dictionaries
        """
        logger.info(f"Extracting Amazon orders with details from last {days_back} days")

        orders = self.extract_orders(days_back)
        enriched_orders = []

        for order in orders:
            order_id = order.get('AmazonOrderId')

            try:
                # Get order items
                order['OrderItems'] = self.extract_order_items(order_id)

                # Get shipping address (may not be available for all orders)
                order['ShippingAddress'] = self.extract_order_address(order_id)

                enriched_orders.append(order)

            except Exception as e:
                logger.error(f"Error enriching order {order_id}: {e}")
                # Still add the order without enrichment
                enriched_orders.append(order)

        logger.info(f"Enriched {len(enriched_orders)} Amazon orders")
        return enriched_orders

    def test_connection(self) -> bool:
        """
        Test the Amazon SP-API connection

        Returns:
            True if connection successful, False otherwise
        """
        try:
            orders_api = self._get_orders_api()

            # Try to fetch orders from last day as a test
            created_after = (datetime.utcnow() - timedelta(days=1)).isoformat()

            response = orders_api.get_orders(
                CreatedAfter=created_after,
                MarketplaceIds=[self.marketplace.marketplace_id]
            )

            logger.info(f"Successfully connected to Amazon SP-API")
            logger.info(f"Marketplace: {self.marketplace.marketplace_id}")
            return True

        except SellingApiException as e:
            logger.error(f"Failed to connect to Amazon SP-API: {e}")
            return False
        except Exception as e:
            logger.error(f"Error testing Amazon connection: {e}")
            return False
