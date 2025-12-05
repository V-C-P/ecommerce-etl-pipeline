import psycopg2
from psycopg2.extras import execute_values, DictCursor
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SupabaseLoader:
    """Load transformed data into Supabase PostgreSQL database"""

    def __init__(self, db_url: str):
        """
        Initialize database connection

        Args:
            db_url: PostgreSQL connection URL
        """
        self.db_url = db_url
        self.conn = None
        self.cursor = None

    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(self.db_url)
            self.cursor = self.conn.cursor(cursor_factory=DictCursor)
            logger.info("Connected to Supabase database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Disconnected from database")

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()

    def upsert_customer(self, customer: Dict) -> Optional[int]:
        """
        Insert or update a customer

        Args:
            customer: Customer data dictionary

        Returns:
            Customer ID
        """
        query = """
            INSERT INTO customers (
                external_id, platform, email, first_name, last_name, phone,
                total_orders, total_spent, created_at, updated_at
            ) VALUES (
                %(external_id)s, %(platform)s, %(email)s, %(first_name)s, %(last_name)s, %(phone)s,
                %(total_orders)s, %(total_spent)s, %(created_at)s, %(updated_at)s
            )
            ON CONFLICT (external_id, platform)
            DO UPDATE SET
                email = EXCLUDED.email,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                phone = EXCLUDED.phone,
                total_orders = EXCLUDED.total_orders,
                total_spent = EXCLUDED.total_spent,
                updated_at = EXCLUDED.updated_at
            RETURNING id;
        """

        try:
            self.cursor.execute(query, customer)
            customer_id = self.cursor.fetchone()[0]
            self.conn.commit()
            return customer_id
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error upserting customer: {e}")
            raise

    def upsert_product(self, product: Dict) -> Optional[int]:
        """
        Insert or update a product

        Args:
            product: Product data dictionary

        Returns:
            Product ID
        """
        query = """
            INSERT INTO products (
                external_id, platform, sku, title, description, vendor,
                product_type, price, inventory_quantity, image_url, created_at, updated_at
            ) VALUES (
                %(external_id)s, %(platform)s, %(sku)s, %(title)s, %(description)s, %(vendor)s,
                %(product_type)s, %(price)s, %(inventory_quantity)s, %(image_url)s, %(created_at)s, %(updated_at)s
            )
            ON CONFLICT (external_id, platform)
            DO UPDATE SET
                sku = EXCLUDED.sku,
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                vendor = EXCLUDED.vendor,
                product_type = EXCLUDED.product_type,
                price = EXCLUDED.price,
                inventory_quantity = EXCLUDED.inventory_quantity,
                image_url = EXCLUDED.image_url,
                updated_at = EXCLUDED.updated_at
            RETURNING id;
        """

        try:
            self.cursor.execute(query, product)
            product_id = self.cursor.fetchone()[0]
            self.conn.commit()
            return product_id
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error upserting product: {e}")
            raise

    def upsert_order(self, order: Dict) -> Optional[int]:
        """
        Insert or update an order

        Args:
            order: Order data dictionary

        Returns:
            Order ID
        """
        # First, get customer_id if customer_external_id is provided
        customer_id = None
        if order.get('customer_external_id'):
            customer_id = self.get_customer_id_by_external_id(
                order['customer_external_id'],
                order['platform']
            )

        query = """
            INSERT INTO orders (
                external_id, platform, order_number, customer_id, email,
                total_price, subtotal_price, total_tax, total_discounts, total_shipping, currency,
                financial_status, fulfillment_status, order_status,
                shipping_name, shipping_address_1, shipping_address_2, shipping_city,
                shipping_province, shipping_country, shipping_zip,
                order_date, processed_at, cancelled_at, created_at, updated_at
            ) VALUES (
                %(external_id)s, %(platform)s, %(order_number)s, %(customer_id)s, %(email)s,
                %(total_price)s, %(subtotal_price)s, %(total_tax)s, %(total_discounts)s, %(total_shipping)s, %(currency)s,
                %(financial_status)s, %(fulfillment_status)s, %(order_status)s,
                %(shipping_name)s, %(shipping_address_1)s, %(shipping_address_2)s, %(shipping_city)s,
                %(shipping_province)s, %(shipping_country)s, %(shipping_zip)s,
                %(order_date)s, %(processed_at)s, %(cancelled_at)s, %(created_at)s, %(updated_at)s
            )
            ON CONFLICT (external_id, platform)
            DO UPDATE SET
                order_number = EXCLUDED.order_number,
                customer_id = EXCLUDED.customer_id,
                email = EXCLUDED.email,
                total_price = EXCLUDED.total_price,
                subtotal_price = EXCLUDED.subtotal_price,
                total_tax = EXCLUDED.total_tax,
                total_discounts = EXCLUDED.total_discounts,
                total_shipping = EXCLUDED.total_shipping,
                currency = EXCLUDED.currency,
                financial_status = EXCLUDED.financial_status,
                fulfillment_status = EXCLUDED.fulfillment_status,
                order_status = EXCLUDED.order_status,
                shipping_name = EXCLUDED.shipping_name,
                shipping_address_1 = EXCLUDED.shipping_address_1,
                shipping_address_2 = EXCLUDED.shipping_address_2,
                shipping_city = EXCLUDED.shipping_city,
                shipping_province = EXCLUDED.shipping_province,
                shipping_country = EXCLUDED.shipping_country,
                shipping_zip = EXCLUDED.shipping_zip,
                order_date = EXCLUDED.order_date,
                processed_at = EXCLUDED.processed_at,
                cancelled_at = EXCLUDED.cancelled_at,
                updated_at = EXCLUDED.updated_at
            RETURNING id;
        """

        try:
            order_data = order.copy()
            order_data['customer_id'] = customer_id
            self.cursor.execute(query, order_data)
            order_id = self.cursor.fetchone()[0]
            self.conn.commit()
            return order_id
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error upserting order: {e}")
            logger.error(f"Order data: {order}")
            raise

    def upsert_line_item(self, line_item: Dict, order_id: int) -> Optional[int]:
        """
        Insert or update an order line item

        Args:
            line_item: Line item data dictionary
            order_id: Database order ID

        Returns:
            Line item ID
        """
        # Get product_id if product_external_id is provided
        product_id = None
        if line_item.get('product_external_id'):
            # Assume same platform as order
            product_id = self.get_product_id_by_external_id(
                line_item['product_external_id'],
                'shopify'  # This should be passed from context
            )

        query = """
            INSERT INTO order_line_items (
                external_id, order_id, product_id, sku, title, variant_title,
                quantity, price, total_discount, tax, fulfillment_status, requires_shipping
            ) VALUES (
                %(external_id)s, %(order_id)s, %(product_id)s, %(sku)s, %(title)s, %(variant_title)s,
                %(quantity)s, %(price)s, %(total_discount)s, %(tax)s, %(fulfillment_status)s, %(requires_shipping)s
            )
            ON CONFLICT (external_id)
            DO UPDATE SET
                product_id = EXCLUDED.product_id,
                sku = EXCLUDED.sku,
                title = EXCLUDED.title,
                variant_title = EXCLUDED.variant_title,
                quantity = EXCLUDED.quantity,
                price = EXCLUDED.price,
                total_discount = EXCLUDED.total_discount,
                tax = EXCLUDED.tax,
                fulfillment_status = EXCLUDED.fulfillment_status,
                requires_shipping = EXCLUDED.requires_shipping,
                updated_at = NOW()
            RETURNING id;
        """

        try:
            item_data = line_item.copy()
            item_data['order_id'] = order_id
            item_data['product_id'] = product_id
            self.cursor.execute(query, item_data)
            line_item_id = self.cursor.fetchone()[0]
            self.conn.commit()
            return line_item_id
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error upserting line item: {e}")
            raise

    def upsert_fulfillment(self, fulfillment: Dict, order_id: int) -> Optional[int]:
        """
        Insert or update a fulfillment

        Args:
            fulfillment: Fulfillment data dictionary
            order_id: Database order ID

        Returns:
            Fulfillment ID
        """
        query = """
            INSERT INTO fulfillments (
                external_id, order_id, platform, status, tracking_company,
                tracking_number, tracking_url, shipped_at, created_at, updated_at
            ) VALUES (
                %(external_id)s, %(order_id)s, %(platform)s, %(status)s, %(tracking_company)s,
                %(tracking_number)s, %(tracking_url)s, %(shipped_at)s, %(created_at)s, %(updated_at)s
            )
            ON CONFLICT (external_id, platform)
            DO UPDATE SET
                status = EXCLUDED.status,
                tracking_company = EXCLUDED.tracking_company,
                tracking_number = EXCLUDED.tracking_number,
                tracking_url = EXCLUDED.tracking_url,
                shipped_at = EXCLUDED.shipped_at,
                updated_at = EXCLUDED.updated_at
            RETURNING id;
        """

        try:
            fulfillment_data = fulfillment.copy()
            fulfillment_data['order_id'] = order_id
            self.cursor.execute(query, fulfillment_data)
            fulfillment_id = self.cursor.fetchone()[0]
            self.conn.commit()
            return fulfillment_id
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error upserting fulfillment: {e}")
            raise

    def get_customer_id_by_external_id(self, external_id: str, platform: str) -> Optional[int]:
        """Get internal customer ID by external ID"""
        query = "SELECT id FROM customers WHERE external_id = %s AND platform = %s"
        self.cursor.execute(query, (external_id, platform))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def get_product_id_by_external_id(self, external_id: str, platform: str) -> Optional[int]:
        """Get internal product ID by external ID"""
        query = "SELECT id FROM products WHERE external_id = %s AND platform = %s"
        self.cursor.execute(query, (external_id, platform))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def get_order_id_by_external_id(self, external_id: str, platform: str) -> Optional[int]:
        """Get internal order ID by external ID"""
        query = "SELECT id FROM orders WHERE external_id = %s AND platform = %s"
        self.cursor.execute(query, (external_id, platform))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def create_sync_log(self, platform: str, sync_type: str) -> int:
        """
        Create a new sync log entry

        Args:
            platform: Platform name ('shopify' or 'amazon')
            sync_type: Type of sync ('orders', 'products', 'customers', 'full')

        Returns:
            Sync log ID
        """
        query = """
            INSERT INTO sync_logs (platform, sync_type, status, started_at)
            VALUES (%s, %s, 'started', NOW())
            RETURNING id;
        """
        self.cursor.execute(query, (platform, sync_type))
        sync_id = self.cursor.fetchone()[0]
        self.conn.commit()
        return sync_id

    def update_sync_log(self, sync_id: int, status: str, records_processed: int = 0,
                        records_inserted: int = 0, records_updated: int = 0,
                        records_failed: int = 0, error_message: Optional[str] = None):
        """
        Update sync log with completion status

        Args:
            sync_id: Sync log ID
            status: Status ('completed' or 'failed')
            records_processed: Number of records processed
            records_inserted: Number of records inserted
            records_updated: Number of records updated
            records_failed: Number of records that failed
            error_message: Error message if failed
        """
        query = """
            UPDATE sync_logs
            SET status = %s,
                records_processed = %s,
                records_inserted = %s,
                records_updated = %s,
                records_failed = %s,
                error_message = %s,
                completed_at = NOW(),
                duration_seconds = EXTRACT(EPOCH FROM (NOW() - started_at))
            WHERE id = %s;
        """
        self.cursor.execute(query, (
            status, records_processed, records_inserted, records_updated,
            records_failed, error_message, sync_id
        ))
        self.conn.commit()

    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            self.cursor.execute("SELECT 1")
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
