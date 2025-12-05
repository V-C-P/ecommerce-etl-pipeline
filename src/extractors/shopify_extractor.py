import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ShopifyExtractor:
    """Extract data from Shopify REST Admin API"""

    def __init__(self, store_url: str, access_token: str, api_version: str = "2024-01"):
        """
        Initialize Shopify API client

        Args:
            store_url: Your Shopify store URL (e.g., 'mystore.myshopify.com')
            access_token: Shopify Admin API access token
            api_version: API version to use (default: 2024-01)
        """
        self.store_url = store_url.replace('https://', '').replace('http://', '')
        self.access_token = access_token
        self.api_version = api_version
        self.base_url = f"https://{self.store_url}/admin/api/{api_version}"
        self.headers = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json"
        }

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Make a request to Shopify API with error handling

        Args:
            endpoint: API endpoint (e.g., '/orders.json')
            params: Query parameters

        Returns:
            Response JSON data
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()

            # Check for rate limiting
            if 'X-Shopify-Shop-Api-Call-Limit' in response.headers:
                limit_info = response.headers['X-Shopify-Shop-Api-Call-Limit']
                logger.info(f"Shopify API rate limit: {limit_info}")

            return response.json()

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error calling Shopify API: {e}")
            logger.error(f"Response: {e.response.text if e.response else 'No response'}")
            raise
        except Exception as e:
            logger.error(f"Error calling Shopify API: {e}")
            raise

    def _paginate(self, endpoint: str, resource_key: str, params: Optional[Dict] = None, limit: int = 250) -> List[Dict]:
        """
        Handle pagination for Shopify API requests

        Args:
            endpoint: API endpoint
            resource_key: Key in response containing the data (e.g., 'orders')
            params: Query parameters
            limit: Results per page (max 250)

        Returns:
            List of all resources
        """
        if params is None:
            params = {}

        params['limit'] = min(limit, 250)
        all_resources = []

        while True:
            data = self._make_request(endpoint, params)
            resources = data.get(resource_key, [])

            if not resources:
                break

            all_resources.extend(resources)
            logger.info(f"Fetched {len(resources)} {resource_key}, total: {len(all_resources)}")

            # Check for pagination using Link header
            # Shopify uses cursor-based pagination
            # For simplicity, we'll use page-based for now
            if len(resources) < params['limit']:
                break

            # Update params for next page
            if 'since_id' in params:
                params['since_id'] = resources[-1]['id']
            elif 'page' in params:
                params['page'] += 1
            else:
                params['page'] = 2

        return all_resources

    def extract_orders(self, days_back: int = 7, status: str = "any") -> List[Dict]:
        """
        Extract orders from Shopify

        Args:
            days_back: Number of days to look back
            status: Order status filter ('open', 'closed', 'any')

        Returns:
            List of order dictionaries
        """
        logger.info(f"Extracting Shopify orders from last {days_back} days")

        created_at_min = (datetime.utcnow() - timedelta(days=days_back)).isoformat()

        params = {
            "status": status,
            "created_at_min": created_at_min,
            "limit": 250
        }

        orders = self._paginate("/orders.json", "orders", params)
        logger.info(f"Extracted {len(orders)} orders from Shopify")

        return orders

    def extract_order_by_id(self, order_id: str) -> Dict:
        """
        Extract a single order by ID

        Args:
            order_id: Shopify order ID

        Returns:
            Order dictionary
        """
        logger.info(f"Extracting Shopify order {order_id}")
        data = self._make_request(f"/orders/{order_id}.json")
        return data.get('order', {})

    def extract_customers(self, days_back: int = 7) -> List[Dict]:
        """
        Extract customers from Shopify

        Args:
            days_back: Number of days to look back

        Returns:
            List of customer dictionaries
        """
        logger.info(f"Extracting Shopify customers from last {days_back} days")

        created_at_min = (datetime.utcnow() - timedelta(days=days_back)).isoformat()

        params = {
            "created_at_min": created_at_min,
            "limit": 250
        }

        customers = self._paginate("/customers.json", "customers", params)
        logger.info(f"Extracted {len(customers)} customers from Shopify")

        return customers

    def extract_products(self, days_back: Optional[int] = None) -> List[Dict]:
        """
        Extract products from Shopify

        Args:
            days_back: Number of days to look back (None for all products)

        Returns:
            List of product dictionaries
        """
        logger.info("Extracting Shopify products")

        params = {"limit": 250}

        if days_back:
            updated_at_min = (datetime.utcnow() - timedelta(days=days_back)).isoformat()
            params["updated_at_min"] = updated_at_min

        products = self._paginate("/products.json", "products", params)
        logger.info(f"Extracted {len(products)} products from Shopify")

        return products

    def extract_fulfillments(self, order_id: str) -> List[Dict]:
        """
        Extract fulfillments for a specific order

        Args:
            order_id: Shopify order ID

        Returns:
            List of fulfillment dictionaries
        """
        logger.info(f"Extracting fulfillments for order {order_id}")

        data = self._make_request(f"/orders/{order_id}/fulfillments.json")
        fulfillments = data.get('fulfillments', [])

        logger.info(f"Extracted {len(fulfillments)} fulfillments for order {order_id}")

        return fulfillments

    def test_connection(self) -> bool:
        """
        Test the Shopify API connection

        Returns:
            True if connection successful, False otherwise
        """
        try:
            data = self._make_request("/shop.json")
            shop_name = data.get('shop', {}).get('name', 'Unknown')
            logger.info(f"Successfully connected to Shopify store: {shop_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Shopify: {e}")
            return False
