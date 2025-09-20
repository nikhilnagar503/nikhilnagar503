"""
Risk & Security Agent for analyzing security risks and dependency changes
"""

from typing import Dict, List, Any
import re

from app.agents.base import AbstractAgent
from app.models.schemas import PRContext, AgentResult, SecretDetection, DependencyChange
from app.services.secret_scanner import SecretScanner
from app.services.dependency_scanner import DependencyScanner
from app.services.risk_scorer import RiskScorer
from app.logging import get_logger

logger = get_logger(__name__)


class RiskSecurityAgent(AbstractAgent):
    """Agent for analyzing security risks and dependency changes"""
    
    def __init__(self):
        super().__init__("risk_security")
        self.secret_scanner = SecretScanner()
        self.dependency_scanner = DependencyScanner()
        self.risk_scorer = RiskScorer()
    
    def run(self, ctx: PRContext) -> AgentResult:
        """Run risk and security analysis"""
        logger.info(f"Running {self.name} agent", repo=ctx.repo_full_name, pr=ctx.pr_number)
        
        warnings = []
        secrets_detected = []
        dependency_changes = []
        risk_factors = []
        
        try:
            # 1. Scan for secrets in changed files
            secrets_detected = self._scan_for_secrets(ctx)
            if secrets_detected:
                risk_factors.append(f"Potential secrets detected: {len(secrets_detected)} occurrences")
            
            # 2. Analyze dependency changes
            dependency_changes = self._analyze_dependency_changes(ctx)
            if dependency_changes:
                high_risk_deps = [d for d in dependency_changes if d.risk_level == 'high']
                if high_risk_deps:
                    risk_factors.append(f"High-risk dependency changes: {len(high_risk_deps)} packages")
            
            # 3. Analyze file changes for security implications
            security_factors = self._analyze_security_implications(ctx)
            risk_factors.extend(security_factors)
            
            # 4. Calculate overall risk score
            risk_score = self.risk_scorer.calculate_risk_score({
                'secrets_count': len(secrets_detected),
                'total_additions': sum(f.additions for f in ctx.files),
                'dependency_changes': dependency_changes,
                'security_files_changed': len([f for f in ctx.files if self._is_security_file(f.filename)]),
                'large_files_changed': len([f for f in ctx.files if f.additions + f.deletions > 200])
            })
            
            payload = {
                "risk_score": risk_score,
                "risk_factors": risk_factors,
                "secrets_detected": [s.dict() for s in secrets_detected],
                "dependency_changes": [d.dict() for d in dependency_changes],
                "security_analysis": {
                    "secrets_count": len(secrets_detected),
                    "high_risk_dependencies": len([d for d in dependency_changes if d.risk_level == 'high']),
                    "security_files_modified": len([f for f in ctx.files if self._is_security_file(f.filename)])
                }
            }
            
            return self._create_result(payload, warnings)
            
        except Exception as e:
            logger.error(f"Error in {self.name} agent", error=str(e), exc_info=True)
            warnings.append(f"Error during security analysis: {str(e)}")
            
            # Return minimal result with basic risk assessment
            basic_risk = min(100, len(ctx.files) * 5 + sum(f.additions for f in ctx.files) // 100)
            
            return self._create_result({
                "risk_score": basic_risk,
                "risk_factors": ["Unable to complete full security analysis"],
                "secrets_detected": [],
                "dependency_changes": [],
                "security_analysis": {"error": str(e)}
            }, warnings)
    
    def _scan_for_secrets(self, ctx: PRContext) -> List[SecretDetection]:
        """Scan changed files for potential secrets"""
        secrets = []
        
        for file in ctx.files:
            # Skip binary files and large files
            if self._is_binary_file(file.filename) or not file.patch:
                continue
            
            # Scan the patch (only added lines)
            file_secrets = self.secret_scanner.scan_diff(file.patch, file.filename)
            secrets.extend(file_secrets)
        
        # Also scan dependency files for embedded secrets
        for filename, content in ctx.dependency_files.items():
            if content:
                file_secrets = self.secret_scanner.scan_content(content, filename)
                secrets.extend(file_secrets)
        
        return secrets
    
    def _analyze_dependency_changes(self, ctx: PRContext) -> List[DependencyChange]:
        """Analyze changes to dependency files"""
        changes = []
        
        for filename, content in ctx.dependency_files.items():
            if not content:
                continue
            
            try:
                file_changes = self.dependency_scanner.analyze_dependency_file(filename, content, ctx)
                changes.extend(file_changes)
            except Exception as e:
                logger.warning(f"Could not analyze dependency file {filename}: {e}")
        
        return changes
    
    def _analyze_security_implications(self, ctx: PRContext) -> List[str]:
        """Analyze files for security implications"""
        security_factors = []
        
        # Check for changes to security-sensitive files
        security_files = [f for f in ctx.files if self._is_security_file(f.filename)]
        if security_files:
            security_factors.append(f"Security-sensitive files modified: {len(security_files)} files")
        
        # Check for authentication/authorization changes
        auth_files = [f for f in ctx.files if self._is_auth_file(f.filename)]
        if auth_files:
            security_factors.append(f"Authentication/authorization files modified: {len(auth_files)} files")
        
        # Check for configuration changes that might affect security
        config_files = [f for f in ctx.files if self._is_config_file(f.filename)]
        if config_files:
            # Look for security-related config changes
            security_config_files = []
            for file in config_files:
                if file.patch and any(keyword in file.patch.lower() for keyword in 
                                    ['password', 'secret', 'key', 'token', 'auth', 'security', 'ssl', 'tls']):
                    security_config_files.append(file.filename)
            
            if security_config_files:
                security_factors.append(f"Security configuration changes detected in: {', '.join(security_config_files)}")
        
        # Check for large deletions (potential data loss)
        large_deletions = [f for f in ctx.files if f.deletions > 100]
        if large_deletions:
            security_factors.append(f"Large deletions detected: {len(large_deletions)} files with significant content removal")
        
        # Check for database migration or schema changes
        db_files = [f for f in ctx.files if self._is_database_file(f.filename)]
        if db_files:
            security_factors.append(f"Database/migration files modified: {len(db_files)} files")
        
        # Check for Docker or deployment configuration changes
        deploy_files = [f for f in ctx.files if self._is_deployment_file(f.filename)]
        if deploy_files:
            security_factors.append(f"Deployment configuration changes: {len(deploy_files)} files")
        
        return security_factors
    
    def _is_security_file(self, filename: str) -> bool:
        """Check if file is security-related"""
        security_patterns = [
            'security', 'sec_', 'crypto', 'encryption', 'decrypt',
            'certificate', 'cert', 'ssl', 'tls', 'key', 'token',
            'password', 'passwd', 'secret', 'private'
        ]
        filename_lower = filename.lower()
        return any(pattern in filename_lower for pattern in security_patterns)
    
    def _is_auth_file(self, filename: str) -> bool:
        """Check if file is authentication/authorization related"""
        auth_patterns = [
            'auth', 'login', 'logout', 'signin', 'signup',
            'permission', 'role', 'access', 'oauth', 'jwt',
            'session', 'middleware/auth', 'guards/', 'decorators/auth'
        ]
        filename_lower = filename.lower()
        return any(pattern in filename_lower for pattern in auth_patterns)
    
    def _is_config_file(self, filename: str) -> bool:
        """Check if file is a configuration file"""
        config_patterns = [
            '.env', '.ini', '.conf', '.config', 'settings',
            '.yml', '.yaml', '.json', 'docker', 'makefile'
        ]
        filename_lower = filename.lower()
        return any(pattern in filename_lower for pattern in config_patterns)
    
    def _is_database_file(self, filename: str) -> bool:
        """Check if file is database-related"""
        db_patterns = [
            'migration', 'migrate', 'schema', 'database', 'db_',
            '.sql', 'models/', 'entity/', 'repository/'
        ]
        filename_lower = filename.lower()
        return any(pattern in filename_lower for pattern in db_patterns)
    
    def _is_deployment_file(self, filename: str) -> bool:
        """Check if file is deployment-related"""
        deploy_patterns = [
            'dockerfile', 'docker-compose', '.github/workflows',
            'deploy', 'deployment', 'terraform', '.tf',
            'kubernetes', 'k8s', 'helm', 'ansible'
        ]
        filename_lower = filename.lower()
        return any(pattern in filename_lower for pattern in deploy_patterns)
    
    def _is_binary_file(self, filename: str) -> bool:
        """Check if file is binary"""
        binary_extensions = [
            '.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip', '.tar', '.gz',
            '.exe', '.dll', '.so', '.dylib', '.bin'
        ]
        return any(filename.lower().endswith(ext) for ext in binary_extensions)