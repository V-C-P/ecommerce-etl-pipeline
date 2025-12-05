-- E-commerce Data Centralization Schema
-- This schema supports data from Shopify and Amazon

-- ============================================
-- CUSTOMERS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS customers (
    id BIGSERIAL PRIMARY KEY,
    external_id VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL, -- 'shopify' or 'amazon'
    email VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    phone VARCHAR(50),
    total_orders INTEGER DEFAULT 0,
    total_spent DECIMAL(10, 2) DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(external_id, platform)
);

CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_platform ON customers(platform);
CREATE INDEX idx_customers_external_id ON customers(external_id);

-- ============================================
-- PRODUCTS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS products (
    id BIGSERIAL PRIMARY KEY,
    external_id VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL, -- 'shopify' or 'amazon'
    sku VARCHAR(255),
    title VARCHAR(500),
    description TEXT,
    vendor VARCHAR(255),
    product_type VARCHAR(255),
    price DECIMAL(10, 2),
    inventory_quantity INTEGER,
    image_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(external_id, platform)
);

CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_products_platform ON products(platform);
CREATE INDEX idx_products_external_id ON products(external_id);

-- ============================================
-- ORDERS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS orders (
    id BIGSERIAL PRIMARY KEY,
    external_id VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL, -- 'shopify' or 'amazon'
    order_number VARCHAR(255),
    customer_id BIGINT REFERENCES customers(id),
    email VARCHAR(255),

    -- Financial info
    total_price DECIMAL(10, 2),
    subtotal_price DECIMAL(10, 2),
    total_tax DECIMAL(10, 2),
    total_discounts DECIMAL(10, 2),
    total_shipping DECIMAL(10, 2),
    currency VARCHAR(10),

    -- Status
    financial_status VARCHAR(50), -- 'pending', 'paid', 'refunded', etc.
    fulfillment_status VARCHAR(50), -- 'fulfilled', 'partial', 'unfulfilled', etc.
    order_status VARCHAR(50), -- 'open', 'closed', 'cancelled'

    -- Shipping info
    shipping_name VARCHAR(255),
    shipping_address_1 VARCHAR(255),
    shipping_address_2 VARCHAR(255),
    shipping_city VARCHAR(255),
    shipping_province VARCHAR(255),
    shipping_country VARCHAR(255),
    shipping_zip VARCHAR(50),

    -- Dates
    order_date TIMESTAMP WITH TIME ZONE,
    processed_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(external_id, platform)
);

CREATE INDEX idx_orders_order_number ON orders(order_number);
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_platform ON orders(platform);
CREATE INDEX idx_orders_order_date ON orders(order_date);
CREATE INDEX idx_orders_financial_status ON orders(financial_status);
CREATE INDEX idx_orders_fulfillment_status ON orders(fulfillment_status);
CREATE INDEX idx_orders_external_id ON orders(external_id);

-- ============================================
-- ORDER LINE ITEMS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS order_line_items (
    id BIGSERIAL PRIMARY KEY,
    external_id VARCHAR(255),
    order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id BIGINT REFERENCES products(id),

    -- Product info
    sku VARCHAR(255),
    title VARCHAR(500),
    variant_title VARCHAR(255),

    -- Pricing
    quantity INTEGER NOT NULL,
    price DECIMAL(10, 2),
    total_discount DECIMAL(10, 2) DEFAULT 0.00,
    tax DECIMAL(10, 2) DEFAULT 0.00,

    -- Fulfillment
    fulfillment_status VARCHAR(50),
    requires_shipping BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_line_items_order_id ON order_line_items(order_id);
CREATE INDEX idx_line_items_product_id ON order_line_items(product_id);
CREATE INDEX idx_line_items_sku ON order_line_items(sku);

-- ============================================
-- FULFILLMENTS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS fulfillments (
    id BIGSERIAL PRIMARY KEY,
    external_id VARCHAR(255) NOT NULL,
    order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,

    status VARCHAR(50), -- 'pending', 'success', 'cancelled', 'error'
    tracking_company VARCHAR(255),
    tracking_number VARCHAR(255),
    tracking_url TEXT,

    shipped_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(external_id, platform)
);

CREATE INDEX idx_fulfillments_order_id ON fulfillments(order_id);
CREATE INDEX idx_fulfillments_tracking_number ON fulfillments(tracking_number);
CREATE INDEX idx_fulfillments_status ON fulfillments(status);

-- ============================================
-- SYNC LOGS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS sync_logs (
    id BIGSERIAL PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    sync_type VARCHAR(50) NOT NULL, -- 'orders', 'products', 'customers', 'full'
    status VARCHAR(50) NOT NULL, -- 'started', 'completed', 'failed'

    records_processed INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,

    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER
);

CREATE INDEX idx_sync_logs_platform ON sync_logs(platform);
CREATE INDEX idx_sync_logs_status ON sync_logs(status);
CREATE INDEX idx_sync_logs_started_at ON sync_logs(started_at);

-- ============================================
-- VIEWS FOR ANALYTICS
-- ============================================

-- Sales by platform
CREATE OR REPLACE VIEW sales_by_platform AS
SELECT
    platform,
    COUNT(*) as order_count,
    SUM(total_price) as total_revenue,
    AVG(total_price) as avg_order_value,
    DATE_TRUNC('day', order_date) as order_day
FROM orders
WHERE financial_status = 'paid'
GROUP BY platform, DATE_TRUNC('day', order_date);

-- Top products
CREATE OR REPLACE VIEW top_products AS
SELECT
    p.title,
    p.sku,
    p.platform,
    COUNT(oli.id) as times_ordered,
    SUM(oli.quantity) as total_quantity_sold,
    SUM(oli.price * oli.quantity) as total_revenue
FROM products p
JOIN order_line_items oli ON p.id = oli.product_id
JOIN orders o ON oli.order_id = o.id
WHERE o.financial_status = 'paid'
GROUP BY p.id, p.title, p.sku, p.platform
ORDER BY total_revenue DESC;

-- Customer lifetime value
CREATE OR REPLACE VIEW customer_lifetime_value AS
SELECT
    c.id,
    c.email,
    c.first_name,
    c.last_name,
    c.platform,
    COUNT(o.id) as order_count,
    SUM(o.total_price) as lifetime_value,
    AVG(o.total_price) as avg_order_value,
    MIN(o.order_date) as first_order_date,
    MAX(o.order_date) as last_order_date
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id
WHERE o.financial_status = 'paid'
GROUP BY c.id, c.email, c.first_name, c.last_name, c.platform;
