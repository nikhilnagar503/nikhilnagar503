"""
Webhook validation utilities
"""

import hmac
import hashlib
from typing import Optional


def validate_webhook_signature(
    payload: bytes, 
    signature: str, 
    secret: str
) -> bool:
    """
    Validate GitHub webhook signature using HMAC SHA256
    
    Args:
        payload: Raw request body bytes
        signature: X-Hub-Signature-256 header value
        secret: Webhook secret
        
    Returns:
        True if signature is valid, False otherwise
    """
    if not signature.startswith("sha256="):
        return False
    
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    received_signature = signature[7:]  # Remove "sha256=" prefix
    
    return hmac.compare_digest(expected_signature, received_signature)


def extract_pr_context(payload: dict) -> Optional[dict]:
    """
    Extract relevant PR context from webhook payload
    
    Args:
        payload: GitHub webhook payload
        
    Returns:
        Extracted PR context or None if invalid
    """
    try:
        pr = payload["pull_request"]
        repo = payload["repository"]
        
        return {
            "repo_full_name": repo["full_name"],
            "repo_owner": repo["owner"]["login"],
            "repo_name": repo["name"],
            "pr_number": pr["number"],
            "pr_title": pr["title"],
            "pr_body": pr["body"],
            "head_sha": pr["head"]["sha"],
            "base_sha": pr["base"]["sha"],
            "head_ref": pr["head"]["ref"],
            "base_ref": pr["base"]["ref"],
            "author": pr["user"]["login"],
            "installation_id": payload.get("installation", {}).get("id"),
            "labels": [label["name"] for label in pr.get("labels", [])]
        }
    except KeyError:
        return None