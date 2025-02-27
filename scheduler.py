import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import and_

from app.core.logging import setup_logging
from app.db.models import IntegrationJob, JobStatus
from app.db.session import SessionLocal

# Set up logging
setup_logging()
logger = logging.getLogger("nasajon_integration")

async def cleanup_stuck_jobs():
    """
    Find and update jobs that have been stuck in PROCESSING state
    for more than 1 hour and mark them as FAILED.
    """
    logger.info("Running job cleanup task")
    db = SessionLocal()
    
    try:
        # Find jobs that have been in PROCESSING state for more than 1 hour
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        stuck_jobs = db.query(IntegrationJob).filter(
            and_(
                IntegrationJob.status == JobStatus.PROCESSING,
                IntegrationJob.started_at < one_hour_ago
            )
        ).all()
        
        for job in stuck_jobs:
            logger.warning(f"Found stuck job: {job.job_id}, marking as FAILED")
            job.status = JobStatus.FAILED
            job.result_message = "Job timed out after processing for more than 1 hour"
            job.completed_at = datetime.utcnow()
        
        if stuck_jobs:
            db.commit()
            logger.info(f"Updated {len(stuck_jobs)} stuck jobs")
    
    finally:
        db.close()

async def purge_old_jobs():
    """
    Find and delete completed or failed jobs that are older than 30 days.
    """
    logger.info("Running job purge task")
    db = SessionLocal()
    
    try:
        # Find completed jobs older than 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        old_jobs = db.query(IntegrationJob).filter(
            and_(
                IntegrationJob.created_at < thirty_days_ago,
                IntegrationJob.status.in_([JobStatus.COMPLETED, JobStatus.FAILED])
            )
        ).all()
        
        if old_jobs:
            count = len(old_jobs)
            for job in old_jobs:
                db.delete(job)
            
            db.commit()
            logger.info(f"Purged {count} old jobs")
    
    finally:
        db.close()

async def run_scheduled_tasks():
    """
    Run scheduled maintenance tasks.
    """
    while True:
        try:
            # Run cleanup tasks
            await cleanup_stuck_jobs()
            await purge_old_jobs()
            
            # Wait for 5 minutes before running again
            await asyncio.sleep(300)
            
        except Exception as e:
            logger.error(f"Error in scheduled tasks: {str(e)}", exc_info=True)
            # Wait a bit before retrying
            await asyncio.sleep(60)

if __name__ == "__main__":
    logger.info("Starting scheduler")
    asyncio.run(run_scheduled_tasks())

