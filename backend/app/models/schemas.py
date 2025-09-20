"""
Pydantic schemas for data validation and serialization
"""

from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class PRFileStatus(str, Enum):
    """PR file change status"""
    ADDED = "added"
    MODIFIED = "modified" 
    REMOVED = "removed"


class RunStatus(str, Enum):
    """PR run status"""
    RECEIVED = "RECEIVED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PRFileModel(BaseModel):
    """Model for a file changed in a PR"""
    filename: str
    status: PRFileStatus
    additions: int
    deletions: int
    changes: int
    patch: Optional[str] = None
    
    class Config:
        use_enum_values = True


class DependencyChange(BaseModel):
    """Model for dependency changes"""
    package: str
    old_version: Optional[str] = None
    new_version: Optional[str] = None
    change_type: str  # added, removed, upgraded, downgraded
    risk_level: str = "low"  # low, medium, high


class SecretDetection(BaseModel):
    """Model for detected secrets"""
    pattern_type: str
    filename: str
    line_number: int
    severity: str = "high"
    # Note: We don't store the actual secret value for security


class TestSuggestion(BaseModel):
    """Model for test suggestions"""
    target_file: str
    function_name: Optional[str] = None
    test_type: str  # positive, negative, boundary
    description: str
    rationale: str
    sample_stub: Optional[str] = None


class ReviewChecklistItem(BaseModel):
    """Model for review checklist items"""
    category: str
    text: str
    severity: str  # low, medium, high
    line_reference: Optional[str] = None


class PRContext(BaseModel):
    """Context data for PR analysis"""
    run_id: str
    repo_full_name: str
    pr_number: int
    head_sha: str
    base_sha: str
    files: List[PRFileModel]
    raw_diff: str
    language_stats: Dict[str, int]
    dependency_files: Dict[str, str]  # filename -> content
    pr_title: str
    pr_body: Optional[str] = None
    author: str
    labels: List[str] = []


class AgentResult(BaseModel):
    """Result from an agent execution"""
    name: str
    payload: Dict[str, Any]
    warnings: List[str] = []
    execution_time_ms: int = 0


class PRAnalysis(BaseModel):
    """Complete PR analysis results"""
    run_id: str
    repo_full_name: str
    pr_number: int
    head_sha: str
    base_sha: str
    
    # Repo scanner results
    summary: str
    changelog: Dict[str, List[str]]
    complexity_flags: List[str] = []
    
    # Risk & security results
    risk_score: int
    risk_factors: List[str] = []
    secrets_detected: List[SecretDetection] = []
    dependency_changes: List[DependencyChange] = []
    
    # Test synthesizer results
    test_suggestions: List[TestSuggestion] = []
    
    # Reviewer results
    review_checklist: List[ReviewChecklistItem] = []
    
    # Metadata
    agent_times_ms: Dict[str, int] = {}
    total_files: int
    total_additions: int
    total_deletions: int
    created_at: datetime = datetime.utcnow()


# Database response models
class PRRunResponse(BaseModel):
    """Response model for PR runs"""
    id: str
    repo_full_name: str
    pr_number: int
    head_sha: str
    base_sha: str
    status: RunStatus
    risk_score: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    processing_ms: Optional[int] = None
    
    class Config:
        use_enum_values = True


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    version: str = "1.0.0"