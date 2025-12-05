# Database Schema Setup

## Overview
This schema is designed to centralize e-commerce data from multiple platforms (Shopify and Amazon) into a single Supabase PostgreSQL database.

## Tables

### Core Tables
- **customers**: Customer information from all platforms
- **products**: Product catalog from all platforms
- **orders**: Order header information
- **order_line_items**: Individual items within each order
- **fulfillments**: Shipping and tracking information
- **sync_logs**: ETL pipeline execution logs

## Setup Instructions

### 1. Access Supabase SQL Editor
1. Log into your Supabase project at https://app.supabase.com
2. Navigate to the SQL Editor in the left sidebar
3. Create a new query

### 2. Run the Schema
1. Copy the contents of `schema.sql`
2. Paste into the SQL Editor
3. Click "Run" to execute

### 3. Verify Installation
Run this query to verify all tables were created:
```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

You should see:
- customers
- products
- orders
- order_line_items
- fulfillments
- sync_logs

### 4. Get Database Connection String
1. Go to Project Settings > Database
2. Copy the connection string under "Connection string"
3. Use URI format: `postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres`
4. Add this to your `.env` file as `SUPABASE_DB_URL`

## Analytics Views

The schema includes three pre-built views for analytics:

- **sales_by_platform**: Daily sales metrics by platform
- **top_products**: Best-selling products across all platforms
- **customer_lifetime_value**: Customer purchase history and value

## Schema Features

- **Platform Agnostic**: Supports data from multiple e-commerce platforms
- **Referential Integrity**: Foreign key constraints maintain data relationships
- **Indexes**: Optimized for common query patterns
- **Deduplication**: UNIQUE constraints prevent duplicate records
- **Audit Trail**: Tracks creation and update timestamps
- **Sync Monitoring**: Logs table tracks ETL pipeline performance
