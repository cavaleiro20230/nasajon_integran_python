import logging
from app.core.logging import setup_logging
from app.tasks.integration_tasks import celery_app

# Set up logging
setup_logging()
logger = logging.getLogger("nasajon_integration")

if __name__ == "__main__":
    logger.info("Starting Celery worker")
    celery_app.start()

