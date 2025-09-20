"""
Orchestrator for running the PR analysis pipeline
"""

import time
from typing import Dict, Any, List
from dataclasses import dataclass

from app.logging import get_logger
from app.config import get_settings
from app.services.github_client import GitHubClient
from app.services.diff_parser import DiffParser
from app.agents.repo_scanner import RepoScannerAgent
from app.agents.risk_security import RiskSecurityAgent
from app.agents.test_synthesizer import TestSynthesizerAgent
from app.agents.reviewer import ReviewerAgent
from app.services.comment_builder import CommentBuilder
from app.models.schemas import PRContext, PRAnalysis

logger = get_logger(__name__)


@dataclass
class PRRunMetrics:
    """Metrics for a PR analysis run"""
    total_time_ms: int
    agent_times_ms: Dict[str, int]
    total_files: int
    total_additions: int
    total_deletions: int
    risk_score: int


def run_pr_analysis(pr_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the complete PR analysis pipeline
    
    Args:
        pr_data: PR context data from webhook
        
    Returns:
        Analysis results
    """
    start_time = time.time()
    settings = get_settings()
    run_id = pr_data.get('run_id')
    
    logger.info(
        "Starting PR analysis pipeline",
        run_id=run_id,
        repo=pr_data.get("repo_full_name"),
        pr_number=pr_data.get("pr_number")
    )
    
    try:
        # Step 1: Fetch PR data from GitHub
        github_client = GitHubClient(settings)
        pr_context = github_client.build_pr_context(pr_data)
        
        logger.info(
            "Built PR context",
            run_id=run_id,
            files_count=len(pr_context.files),
            additions=sum(f.additions for f in pr_context.files),
            deletions=sum(f.deletions for f in pr_context.files)
        )
        
        # Step 2: Run agent pipeline
        analysis = run_agent_pipeline(pr_context)
        
        # Step 3: Build and post comment
        comment_builder = CommentBuilder()
        comment_markdown = comment_builder.build_comment(analysis)
        
        # Post comment to GitHub
        github_client.post_pr_comment(
            pr_context.repo_full_name,
            pr_context.pr_number,
            comment_markdown
        )
        
        # Calculate metrics
        total_time = int((time.time() - start_time) * 1000)
        metrics = PRRunMetrics(
            total_time_ms=total_time,
            agent_times_ms=analysis.agent_times_ms,
            total_files=len(pr_context.files),
            total_additions=sum(f.additions for f in pr_context.files),
            total_deletions=sum(f.deletions for f in pr_context.files),
            risk_score=analysis.risk_score
        )
        
        logger.info(
            "Completed PR analysis pipeline",
            run_id=run_id,
            total_time_ms=total_time,
            risk_score=analysis.risk_score
        )
        
        return {
            "run_id": run_id,
            "status": "completed",
            "metrics": metrics.__dict__,
            "analysis": analysis.dict(),
            "comment_posted": True
        }
        
    except Exception as e:
        logger.error(
            "Failed PR analysis pipeline",
            run_id=run_id,
            error=str(e),
            exc_info=True
        )
        raise


def run_agent_pipeline(pr_context: PRContext) -> PRAnalysis:
    """
    Run the multi-agent analysis pipeline
    
    Args:
        pr_context: PR context data
        
    Returns:
        Complete analysis results
    """
    logger.info(
        "Starting agent pipeline",
        repo=pr_context.repo_full_name,
        pr_number=pr_context.pr_number
    )
    
    agent_times = {}
    
    # Initialize agents
    agents = [
        ("repo_scanner", RepoScannerAgent()),
        ("risk_security", RiskSecurityAgent()),
        ("test_synthesizer", TestSynthesizerAgent()),
        ("reviewer", ReviewerAgent())
    ]
    
    # Run agents sequentially
    agent_results = {}
    for agent_name, agent in agents:
        start_time = time.time()
        
        logger.info(f"Running {agent_name} agent")
        result = agent.run(pr_context)
        
        agent_time = int((time.time() - start_time) * 1000)
        agent_times[agent_name] = agent_time
        agent_results[agent_name] = result
        
        logger.info(
            f"Completed {agent_name} agent",
            time_ms=agent_time,
            warnings=len(result.warnings)
        )
    
    # Combine results into analysis
    analysis = PRAnalysis(
        run_id=pr_context.run_id,
        repo_full_name=pr_context.repo_full_name,
        pr_number=pr_context.pr_number,
        head_sha=pr_context.head_sha,
        base_sha=pr_context.base_sha,
        
        # Repo scanner results
        summary=agent_results["repo_scanner"].payload.get("summary", ""),
        changelog=agent_results["repo_scanner"].payload.get("changelog", {}),
        complexity_flags=agent_results["repo_scanner"].payload.get("complexity_flags", []),
        
        # Risk & security results  
        risk_score=agent_results["risk_security"].payload.get("risk_score", 0),
        risk_factors=agent_results["risk_security"].payload.get("risk_factors", []),
        secrets_detected=agent_results["risk_security"].payload.get("secrets_detected", []),
        dependency_changes=agent_results["risk_security"].payload.get("dependency_changes", []),
        
        # Test synthesizer results
        test_suggestions=agent_results["test_synthesizer"].payload.get("test_suggestions", []),
        
        # Reviewer results
        review_checklist=agent_results["reviewer"].payload.get("review_checklist", []),
        
        # Metadata
        agent_times_ms=agent_times,
        total_files=len(pr_context.files),
        total_additions=sum(f.additions for f in pr_context.files),
        total_deletions=sum(f.deletions for f in pr_context.files)
    )
    
    logger.info(
        "Completed agent pipeline",
        risk_score=analysis.risk_score,
        test_suggestions_count=len(analysis.test_suggestions),
        review_items_count=len(analysis.review_checklist)
    )
    
    return analysis