"""
Risk scoring utilities for calculating overall PR risk scores
"""

from typing import Dict, List, Any
from app.models.schemas import DependencyChange
from app.logging import get_logger

logger = get_logger(__name__)


class RiskScorer:
    """Calculator for PR risk scores"""
    
    def __init__(self):
        self.base_score = 0
        self.max_score = 100
    
    def calculate_risk_score(self, factors: Dict[str, Any]) -> int:
        """
        Calculate overall risk score based on various factors
        
        Args:
            factors: Dictionary containing risk factors
            
        Returns:
            Risk score from 0-100
        """
        score = self.base_score
        
        # Factor 1: Secrets detected (+25 points)
        secrets_count = factors.get('secrets_count', 0)
        if secrets_count > 0:
            score += 25
            logger.info(f"Risk score +25 for {secrets_count} secrets detected")
        
        # Factor 2: Large changes (+10 points for >1000 additions)
        total_additions = factors.get('total_additions', 0)
        if total_additions > 1000:
            score += 10
            logger.info(f"Risk score +10 for large change ({total_additions} additions)")
        
        # Factor 3: Dependency changes
        dependency_changes = factors.get('dependency_changes', [])
        if isinstance(dependency_changes, list):
            high_risk_deps = len([d for d in dependency_changes if 
                                isinstance(d, dict) and d.get('risk_level') == 'high'])
            if high_risk_deps > 0:
                score += 15
                logger.info(f"Risk score +15 for {high_risk_deps} high-risk dependency changes")
        
        # Factor 4: Security files changed (+10 points)
        security_files_changed = factors.get('security_files_changed', 0)
        if security_files_changed > 0:
            score += 10
            logger.info(f"Risk score +10 for {security_files_changed} security files changed")
        
        # Factor 5: Large individual file changes (+10 points)
        large_files_changed = factors.get('large_files_changed', 0)
        if large_files_changed > 0:
            score += 10
            logger.info(f"Risk score +10 for {large_files_changed} large files changed")
        
        # Factor 6: Additional contextual factors
        
        # Many files changed (spread risk)
        total_files = factors.get('total_files', 0)
        if total_files > 20:
            score += 5
            logger.info(f"Risk score +5 for many files changed ({total_files})")
        
        # Binary files changed
        binary_files = factors.get('binary_files_changed', 0)
        if binary_files > 0:
            score += 5
            logger.info(f"Risk score +5 for {binary_files} binary files changed")
        
        # Database/migration files
        db_files = factors.get('database_files_changed', 0)
        if db_files > 0:
            score += 8
            logger.info(f"Risk score +8 for {db_files} database files changed")
        
        # Configuration files with security implications
        security_config_files = factors.get('security_config_files_changed', 0)
        if security_config_files > 0:
            score += 12
            logger.info(f"Risk score +12 for {security_config_files} security config files changed")
        
        # Deployment/infrastructure files
        deploy_files = factors.get('deployment_files_changed', 0)
        if deploy_files > 0:
            score += 7
            logger.info(f"Risk score +7 for {deploy_files} deployment files changed")
        
        # Large deletions (potential data loss)
        large_deletions = factors.get('large_deletions', 0)
        if large_deletions > 500:
            score += 8
            logger.info(f"Risk score +8 for large deletions ({large_deletions} lines)")
        
        # Normalize to 0-100 range
        final_score = min(self.max_score, max(0, score))
        
        logger.info(f"Calculated final risk score: {final_score}/100")
        return final_score
    
    def get_risk_level_description(self, score: int) -> str:
        """Get human-readable risk level description"""
        if score >= 70:
            return "High Risk - Careful review recommended"
        elif score >= 40:
            return "Medium Risk - Standard review process"
        elif score >= 20:
            return "Low-Medium Risk - Light review needed"
        else:
            return "Low Risk - Minimal review required"
    
    def get_risk_factors_explanation(self) -> Dict[str, str]:
        """Get explanation of risk factors"""
        return {
            "secrets_detected": "Potential secrets or sensitive data found in code (+25 points)",
            "large_additions": "Large number of code additions (>1000 lines) (+10 points)",
            "high_risk_dependencies": "Changes to security-critical dependencies (+15 points)",
            "security_files": "Modifications to security-related files (+10 points)",
            "large_files": "Large changes to individual files (+10 points)",
            "many_files": "Changes spread across many files (+5 points)",
            "binary_files": "Binary files added or modified (+5 points)",
            "database_files": "Database schema or migration changes (+8 points)",
            "security_config": "Security configuration changes (+12 points)",
            "deployment_files": "Infrastructure or deployment changes (+7 points)",
            "large_deletions": "Significant code deletions (+8 points)"
        }