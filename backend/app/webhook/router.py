"""
Webhook router for GitHub events
"""

from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
import hmac
import hashlib
import json
from typing import Dict, Any

from app.config import get_settings
from app.logging import get_logger
from app.webhook.validators import validate_webhook_signature
from app.queue.worker import enqueue_pr_analysis

logger = get_logger(__name__)
router = APIRouter()


@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    settings = Depends(get_settings)
):
    """Handle GitHub webhook events"""
    
    # Get headers
    github_event = request.headers.get("X-GitHub-Event")
    github_delivery = request.headers.get("X-GitHub-Delivery")
    signature = request.headers.get("X-Hub-Signature-256")
    
    if not github_event or not github_delivery:
        raise HTTPException(status_code=400, detail="Missing required headers")
    
    # Get payload
    payload_bytes = await request.body()
    
    try:
        payload = json.loads(payload_bytes.decode('utf-8'))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Validate signature
    if settings.github_webhook_secret:
        if not signature:
            raise HTTPException(status_code=401, detail="Missing signature")
        
        if not validate_webhook_signature(
            payload_bytes, 
            signature, 
            settings.github_webhook_secret
        ):
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    logger.info(
        "Received GitHub webhook",
        event=github_event,
        delivery=github_delivery,
        action=payload.get("action")
    )
    
    # Handle pull request events
    if github_event == "pull_request":
        action = payload.get("action")
        if action in ["opened", "synchronize"]:
            pr_data = {
                "repo_full_name": payload["repository"]["full_name"],
                "pr_number": payload["pull_request"]["number"],
                "head_sha": payload["pull_request"]["head"]["sha"],
                "base_sha": payload["pull_request"]["base"]["sha"],
                "installation_id": payload.get("installation", {}).get("id"),
                "action": action
            }
            
            # Enqueue for background processing
            background_tasks.add_task(enqueue_pr_analysis, pr_data)
            
            logger.info(
                "Enqueued PR analysis",
                repo=pr_data["repo_full_name"],
                pr_number=pr_data["pr_number"],
                action=action
            )
    
    return JSONResponse(content={"status": "received"})


@router.get("/ping")
async def ping():
    """Simple ping endpoint for webhook testing"""
    return {"message": "pong"}