import json
import logging
import os
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.etl_pipeline import ETLPipeline

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    AWS Lambda handler function

    Args:
        event: Lambda event object
        context: Lambda context object

    Returns:
        Response dictionary with status and results
    """
    logger.info("Starting ETL Lambda function")
    logger.info(f"Event: {json.dumps(event)}")

    try:
        # Initialize ETL pipeline
        pipeline = ETLPipeline()

        # Determine what to sync based on event
        sync_type = event.get('sync_type', 'all')

        if sync_type == 'test':
            # Test connections only
            logger.info("Running connection tests")
            results = pipeline.test_connections()
            success = all(results.values())

            return {
                'statusCode': 200 if success else 500,
                'body': json.dumps({
                    'message': 'Connection tests completed',
                    'results': results,
                    'success': success
                })
            }

        elif sync_type == 'shopify':
            # Sync Shopify only
            logger.info("Syncing Shopify only")
            results = pipeline.sync_shopify_orders()

        elif sync_type == 'amazon':
            # Sync Amazon only
            logger.info("Syncing Amazon only")
            results = pipeline.sync_amazon_orders()

        else:
            # Sync all platforms (default)
            logger.info("Syncing all platforms")
            results = pipeline.sync_all()

        # Determine success
        success = results.get('success', True)
        if isinstance(results, dict) and 'errors' in results:
            success = results['errors'] == 0

        logger.info(f"ETL completed with success={success}")

        return {
            'statusCode': 200 if success else 500,
            'body': json.dumps({
                'message': 'ETL pipeline completed',
                'results': results,
                'success': success
            })
        }

    except Exception as e:
        logger.error(f"ETL pipeline failed with error: {e}", exc_info=True)

        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'ETL pipeline failed',
                'error': str(e),
                'success': False
            })
        }


# For local testing
if __name__ == '__main__':
    from dotenv import load_dotenv

    # Load environment variables from .env file
    load_dotenv()

    # Create test event
    test_event = {
        'sync_type': 'test'  # Options: 'test', 'shopify', 'amazon', 'all'
    }

    # Mock context
    class MockContext:
        def __init__(self):
            self.function_name = 'local-test'
            self.memory_limit_in_mb = 512
            self.invoked_function_arn = 'arn:aws:lambda:local:000000000000:function:local-test'
            self.aws_request_id = 'local-test-request-id'

    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2))
