"""
Background worker for processing PR analysis tasks
"""

import json
import uuid
from typing import Dict, Any
import asyncio
from rq import Queue
from rq.job import Job

from app.deps import get_redis_client
from app.logging import get_logger
from app.orchestrator.runner import run_pr_analysis

logger = get_logger(__name__)


def get_queue() -> Queue:
    """Get RQ queue instance"""
    redis_client = get_redis_client()
    return Queue('pr_analysis', connection=redis_client)


def enqueue_pr_analysis(pr_data: Dict[str, Any]) -> str:
    """
    Enqueue PR analysis task
    
    Args:
        pr_data: PR context data from webhook
        
    Returns:
        Job ID
    """
    queue = get_queue()
    
    # Generate unique run ID
    run_id = str(uuid.uuid4())
    pr_data['run_id'] = run_id
    
    # Enqueue job
    job = queue.enqueue(
        process_pr_analysis,
        pr_data,
        job_id=run_id,
        job_timeout='10m'
    )
    
    logger.info(
        "Enqueued PR analysis job",
        job_id=job.id,
        repo=pr_data.get("repo_full_name"),
        pr_number=pr_data.get("pr_number")
    )
    
    return job.id


def process_pr_analysis(pr_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process PR analysis (worker function)
    
    Args:
        pr_data: PR context data
        
    Returns:
        Analysis results
    """
    run_id = pr_data.get('run_id')
    
    logger.info(
        "Starting PR analysis",
        run_id=run_id,
        repo=pr_data.get("repo_full_name"),
        pr_number=pr_data.get("pr_number")
    )
    
    try:
        # Run the analysis pipeline
        result = run_pr_analysis(pr_data)
        
        logger.info(
            "Completed PR analysis",
            run_id=run_id,
            status="success"
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "Failed PR analysis",
            run_id=run_id,
            error=str(e),
            exc_info=True
        )
        raise


def get_job_status(job_id: str) -> Dict[str, Any]:
    """
    Get job status
    
    Args:
        job_id: Job ID
        
    Returns:
        Job status information
    """
    queue = get_queue()
    
    try:
        job = Job.fetch(job_id, connection=queue.connection)
        return {
            "job_id": job_id,
            "status": job.status,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "ended_at": job.ended_at.isoformat() if job.ended_at else None,
            "result": job.result if job.is_finished else None,
            "exc_info": job.exc_info if job.is_failed else None
        }
    except Exception as e:
        return {
            "job_id": job_id,
            "status": "not_found",
            "error": str(e)
        }