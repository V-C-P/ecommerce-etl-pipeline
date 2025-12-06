from .extractors.shopify_extractor import ShopifyExtractor
from .extractors.amazon_extractor import AmazonExtractor
from .transformers.shopify_transformer import ShopifyTransformer
from .transformers.amazon_transformer import AmazonTransformer
from .loaders.supabase_loader import SupabaseLoader
from .config import Config
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class ETLPipeline:
    """Main ETL pipeline orchestrator"""

    def __init__(self):
        """Initialize ETL pipeline with configuration"""
        Config.validate()

        # Initialize extractors
        self.shopify_extractor = ShopifyExtractor(
            store_url=Config.SHOPIFY_STORE_URL,
            access_token=Config.SHOPIFY_ACCESS_TOKEN,
            api_version=Config.SHOPIFY_API_VERSION
        )

        self.amazon_extractor = AmazonExtractor(
            refresh_token=Config.AMAZON_REFRESH_TOKEN,
            client_id=Config.AMAZON_CLIENT_ID,
            client_secret=Config.AMAZON_CLIENT_SECRET,
            marketplace=Config.AMAZON_REGION
        )

        # Initialize transformers
        self.shopify_transformer = ShopifyTransformer()
        self.amazon_transformer = AmazonTransformer()

        # Database URL for loader
        self.db_url = Config.SUPABASE_DB_URL
        self.days_to_sync = Config.DAYS_TO_SYNC

        logger.info("ETL Pipeline initialized")

    def sync_shopify_orders(self) -> Dict:
        """
        Sync Shopify orders to database

        Returns:
            Dictionary with sync statistics
        """
        logger.info("Starting Shopify orders sync")

        stats = {
            'platform': 'shopify',
            'orders_processed': 0,
            'orders_inserted': 0,
            'orders_updated': 0,
            'errors': 0,
            'error_messages': []
        }

        try:
            # Extract orders from Shopify
            logger.info(f"Extracting Shopify orders from last {self.days_to_sync} days")
            raw_orders = self.shopify_extractor.extract_orders(days_back=self.days_to_sync)
            logger.info(f"Extracted {len(raw_orders)} orders from Shopify")

            # Load data to database
            with SupabaseLoader(self.db_url) as loader:
                sync_id = loader.create_sync_log('shopify', 'orders')

                for raw_order in raw_orders:
                    try:
                        # Transform order with details
                        transformed = self.shopify_transformer.transform_order_with_details(raw_order)

                        # Upsert customer if exists
                        customer = raw_order.get('customer')
                        if customer:
                            customer_data = self.shopify_transformer.transform_customer(customer)
                            loader.upsert_customer(customer_data)

                        # Upsert order
                        order_id = loader.upsert_order(transformed['order'])

                        # Upsert line items
                        for line_item in transformed['line_items']:
                            loader.upsert_line_item(line_item, order_id, platform='shopify')

                        # Upsert fulfillments
                        for fulfillment in transformed['fulfillments']:
                            loader.upsert_fulfillment(fulfillment, order_id)

                        stats['orders_processed'] += 1
                        stats['orders_inserted'] += 1

                    except Exception as e:
                        logger.error(f"Error processing Shopify order {raw_order.get('id')}: {e}")
                        stats['errors'] += 1
                        stats['error_messages'].append(str(e))

                # Update sync log
                loader.update_sync_log(
                    sync_id=sync_id,
                    status='completed',
                    records_processed=stats['orders_processed'],
                    records_inserted=stats['orders_inserted'],
                    records_failed=stats['errors']
                )

        except Exception as e:
            logger.error(f"Fatal error in Shopify sync: {e}")
            stats['error_messages'].append(str(e))
            raise

        logger.info(f"Shopify sync completed: {stats}")
        return stats

    def sync_amazon_orders(self) -> Dict:
        """
        Sync Amazon orders to database

        Returns:
            Dictionary with sync statistics
        """
        logger.info("Starting Amazon orders sync")

        stats = {
            'platform': 'amazon',
            'orders_processed': 0,
            'orders_inserted': 0,
            'orders_updated': 0,
            'errors': 0,
            'error_messages': []
        }

        try:
            # Extract orders from Amazon with details
            logger.info(f"Extracting Amazon orders from last {self.days_to_sync} days")
            raw_orders = self.amazon_extractor.extract_orders_with_details(days_back=self.days_to_sync)
            logger.info(f"Extracted {len(raw_orders)} orders from Amazon")

            # Load data to database
            with SupabaseLoader(self.db_url) as loader:
                sync_id = loader.create_sync_log('amazon', 'orders')

                for raw_order in raw_orders:
                    try:
                        # Transform order with details
                        transformed = self.amazon_transformer.transform_order_with_details(raw_order)

                        # Upsert customer
                        loader.upsert_customer(transformed['customer'])

                        # Upsert products
                        for product in transformed.get('products', []):
                            loader.upsert_product(product)

                        # Upsert order
                        order_id = loader.upsert_order(transformed['order'])

                        # Upsert line items
                        for line_item in transformed['line_items']:
                            loader.upsert_line_item(line_item, order_id, platform='amazon')

                        stats['orders_processed'] += 1
                        stats['orders_inserted'] += 1

                    except Exception as e:
                        logger.error(f"Error processing Amazon order {raw_order.get('AmazonOrderId')}: {e}")
                        stats['errors'] += 1
                        stats['error_messages'].append(str(e))

                # Update sync log
                loader.update_sync_log(
                    sync_id=sync_id,
                    status='completed',
                    records_processed=stats['orders_processed'],
                    records_inserted=stats['orders_inserted'],
                    records_failed=stats['errors']
                )

        except Exception as e:
            logger.error(f"Fatal error in Amazon sync: {e}")
            stats['error_messages'].append(str(e))
            raise

        logger.info(f"Amazon sync completed: {stats}")
        return stats

    def sync_all(self) -> Dict:
        """
        Run complete ETL pipeline for all platforms

        Returns:
            Dictionary with combined sync statistics
        """
        logger.info("Starting full ETL pipeline")

        results = {
            'shopify': None,
            'amazon': None,
            'total_orders_processed': 0,
            'success': True
        }

        try:
            # Sync Shopify
            results['shopify'] = self.sync_shopify_orders()
            results['total_orders_processed'] += results['shopify']['orders_processed']

        except Exception as e:
            logger.error(f"Shopify sync failed: {e}")
            results['success'] = False

        try:
            # Sync Amazon
            results['amazon'] = self.sync_amazon_orders()
            results['total_orders_processed'] += results['amazon']['orders_processed']

        except Exception as e:
            logger.error(f"Amazon sync failed: {e}")
            results['success'] = False

        logger.info(f"ETL pipeline completed. Total orders processed: {results['total_orders_processed']}")

        return results

    def test_connections(self) -> Dict:
        """
        Test all connections

        Returns:
            Dictionary with connection test results
        """
        results = {
            'shopify': False,
            'amazon': False,
            'database': False
        }

        # Test Shopify
        try:
            results['shopify'] = self.shopify_extractor.test_connection()
        except Exception as e:
            logger.error(f"Shopify connection test failed: {e}")

        # Test Amazon
        try:
            results['amazon'] = self.amazon_extractor.test_connection()
        except Exception as e:
            logger.error(f"Amazon connection test failed: {e}")

        # Test Database
        try:
            with SupabaseLoader(self.db_url) as loader:
                results['database'] = loader.test_connection()
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")

        return results
