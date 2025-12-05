import os
from typing import Optional


class Config:
    """Configuration manager for ETL pipeline"""

    # Shopify Configuration
    SHOPIFY_STORE_URL: Optional[str] = os.getenv('SHOPIFY_STORE_URL')
    SHOPIFY_ACCESS_TOKEN: Optional[str] = os.getenv('SHOPIFY_ACCESS_TOKEN')
    SHOPIFY_API_VERSION: str = os.getenv('SHOPIFY_API_VERSION', '2024-01')

    # Amazon SP-API Configuration
    AMAZON_REFRESH_TOKEN: Optional[str] = os.getenv('AMAZON_REFRESH_TOKEN')
    AMAZON_CLIENT_ID: Optional[str] = os.getenv('AMAZON_CLIENT_ID')
    AMAZON_CLIENT_SECRET: Optional[str] = os.getenv('AMAZON_CLIENT_SECRET')
    AMAZON_REGION: str = os.getenv('AMAZON_REGION', 'us-east-1')
    AMAZON_MARKETPLACE_ID: Optional[str] = os.getenv('AMAZON_MARKETPLACE_ID')

    # Supabase Configuration
    SUPABASE_URL: Optional[str] = os.getenv('SUPABASE_URL')
    SUPABASE_KEY: Optional[str] = os.getenv('SUPABASE_KEY')
    SUPABASE_DB_URL: Optional[str] = os.getenv('SUPABASE_DB_URL')

    # ETL Configuration
    DAYS_TO_SYNC: int = int(os.getenv('DAYS_TO_SYNC', '7'))
    BATCH_SIZE: int = int(os.getenv('BATCH_SIZE', '100'))

    @classmethod
    def validate(cls) -> bool:
        """Validate that all required configuration is present"""
        required_vars = [
            'SHOPIFY_STORE_URL',
            'SHOPIFY_ACCESS_TOKEN',
            'AMAZON_REFRESH_TOKEN',
            'AMAZON_CLIENT_ID',
            'AMAZON_CLIENT_SECRET',
            'AMAZON_MARKETPLACE_ID',
            'SUPABASE_URL',
            'SUPABASE_KEY',
            'SUPABASE_DB_URL'
        ]

        missing = [var for var in required_vars if not getattr(cls, var)]

        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        return True
