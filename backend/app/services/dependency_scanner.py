"""
Dependency scanner for analyzing changes to dependency files
"""

import re
from typing import List, Dict, Any
from app.models.schemas import DependencyChange, PRContext
from app.logging import get_logger

logger = get_logger(__name__)


class DependencyScanner:
    """Scanner for analyzing dependency file changes"""
    
    def __init__(self):
        self.high_risk_packages = {
            # Python packages
            'cryptography', 'pyjwt', 'requests', 'urllib3', 'flask', 'django',
            'sqlalchemy', 'psycopg2', 'pymongo', 'redis', 'celery',
            
            # JavaScript packages  
            'express', 'axios', 'request', 'lodash', 'moment', 'jquery',
            'react', 'vue', 'angular', 'webpack', 'babel',
            
            # General security-related
            'openssl', 'ssh', 'ssl', 'tls', 'oauth', 'jwt'
        }
    
    def analyze_dependency_file(self, filename: str, content: str, ctx: PRContext) -> List[DependencyChange]:
        """
        Analyze a dependency file for changes
        
        Args:
            filename: Name of the dependency file
            content: Current content of the file
            ctx: PR context for accessing diff information
            
        Returns:
            List of dependency changes
        """
        if filename.endswith(('requirements.txt', 'requirements-dev.txt')):
            return self._analyze_python_requirements(filename, content, ctx)
        elif filename == 'package.json':
            return self._analyze_package_json(filename, content, ctx)
        elif filename in ('Pipfile', 'pyproject.toml'):
            return self._analyze_python_pipfile(filename, content, ctx)
        elif filename in ('go.mod', 'go.sum'):
            return self._analyze_go_mod(filename, content, ctx)
        else:
            logger.warning(f"Unsupported dependency file: {filename}")
            return []
    
    def _analyze_python_requirements(self, filename: str, content: str, ctx: PRContext) -> List[DependencyChange]:
        """Analyze Python requirements.txt file"""
        changes = []
        
        # Find the corresponding file in the PR
        pr_file = next((f for f in ctx.files if f.filename == filename), None)
        if not pr_file or not pr_file.patch:
            return changes
        
        # Parse added and removed lines from patch
        added_lines = []
        removed_lines = []
        
        for line in pr_file.patch.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                added_lines.append(line[1:].strip())
            elif line.startswith('-') and not line.startswith('---'):
                removed_lines.append(line[1:].strip())
        
        # Parse packages from lines
        added_packages = self._parse_python_packages(added_lines)
        removed_packages = self._parse_python_packages(removed_lines)
        
        # Find package changes
        all_packages = set(added_packages.keys()) | set(removed_packages.keys())
        
        for package in all_packages:
            old_version = removed_packages.get(package)
            new_version = added_packages.get(package)
            
            if old_version and new_version:
                # Package version changed
                change_type = self._determine_version_change_type(old_version, new_version)
                changes.append(DependencyChange(
                    package=package,
                    old_version=old_version,
                    new_version=new_version,
                    change_type=change_type,
                    risk_level=self._assess_package_risk(package, change_type)
                ))
            elif new_version and not old_version:
                # Package added
                changes.append(DependencyChange(
                    package=package,
                    old_version=None,
                    new_version=new_version,
                    change_type="added",
                    risk_level=self._assess_package_risk(package, "added")
                ))
            elif old_version and not new_version:
                # Package removed
                changes.append(DependencyChange(
                    package=package,
                    old_version=old_version,
                    new_version=None,
                    change_type="removed",
                    risk_level=self._assess_package_risk(package, "removed")
                ))
        
        return changes
    
    def _analyze_package_json(self, filename: str, content: str, ctx: PRContext) -> List[DependencyChange]:
        """Analyze package.json file"""
        import json
        
        changes = []
        pr_file = next((f for f in ctx.files if f.filename == filename), None)
        if not pr_file or not pr_file.patch:
            return changes
        
        # This is a simplified analysis - in practice, you'd want to parse the JSON diff more carefully
        for line in pr_file.patch.split('\n'):
            if line.startswith('+') and '"' in line and ':' in line:
                # Try to extract package changes from added lines
                match = re.search(r'"([^"]+)":\s*"([^"]+)"', line)
                if match:
                    package, version = match.groups()
                    if not package.startswith('_') and '/' not in package:  # Skip metadata and scoped packages for now
                        changes.append(DependencyChange(
                            package=package,
                            old_version=None,
                            new_version=version,
                            change_type="added",
                            risk_level=self._assess_package_risk(package, "added")
                        ))
        
        return changes
    
    def _analyze_python_pipfile(self, filename: str, content: str, ctx: PRContext) -> List[DependencyChange]:
        """Analyze Pipfile or pyproject.toml"""
        # Similar to requirements.txt but with TOML format
        # This is a simplified implementation
        changes = []
        pr_file = next((f for f in ctx.files if f.filename == filename), None)
        if not pr_file or not pr_file.patch:
            return changes
        
        # Look for dependency additions in TOML format
        for line in pr_file.patch.split('\n'):
            if line.startswith('+') and '=' in line:
                # Match patterns like: package = "version"
                match = re.search(r'([a-zA-Z0-9_-]+)\s*=\s*"([^"]+)"', line)
                if match:
                    package, version = match.groups()
                    changes.append(DependencyChange(
                        package=package,
                        old_version=None,
                        new_version=version,
                        change_type="added",
                        risk_level=self._assess_package_risk(package, "added")
                    ))
        
        return changes
    
    def _analyze_go_mod(self, filename: str, content: str, ctx: PRContext) -> List[DependencyChange]:
        """Analyze go.mod file"""
        changes = []
        pr_file = next((f for f in ctx.files if f.filename == filename), None)
        if not pr_file or not pr_file.patch:
            return changes
        
        # Look for require statements
        for line in pr_file.patch.split('\n'):
            if line.startswith('+') and 'require' in line:
                # Match patterns like: require github.com/package v1.2.3
                match = re.search(r'require\s+([^\s]+)\s+(v[^\s]+)', line)
                if match:
                    package, version = match.groups()
                    changes.append(DependencyChange(
                        package=package,
                        old_version=None,
                        new_version=version,
                        change_type="added",
                        risk_level=self._assess_package_risk(package, "added")
                    ))
        
        return changes
    
    def _parse_python_packages(self, lines: List[str]) -> Dict[str, str]:
        """Parse Python package specifications from lines"""
        packages = {}
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Handle different package specification formats
            # package==1.0.0, package>=1.0.0, package~=1.0.0, etc.
            match = re.match(r'^([a-zA-Z0-9_-]+)([><=~!]+)(.+)$', line)
            if match:
                package, operator, version = match.groups()
                packages[package] = version.strip()
            else:
                # Just package name without version
                if re.match(r'^[a-zA-Z0-9_-]+$', line):
                    packages[line] = "latest"
        
        return packages
    
    def _determine_version_change_type(self, old_version: str, new_version: str) -> str:
        """Determine if version change is upgrade or downgrade"""
        try:
            # Simple version comparison - in practice, you'd use a proper version parsing library
            old_parts = [int(x) for x in old_version.split('.') if x.isdigit()]
            new_parts = [int(x) for x in new_version.split('.') if x.isdigit()]
            
            # Pad shorter version with zeros
            max_len = max(len(old_parts), len(new_parts))
            old_parts.extend([0] * (max_len - len(old_parts)))
            new_parts.extend([0] * (max_len - len(new_parts)))
            
            if new_parts > old_parts:
                return "upgraded"
            elif new_parts < old_parts:
                return "downgraded"
            else:
                return "modified"
        except (ValueError, AttributeError):
            return "modified"
    
    def _assess_package_risk(self, package: str, change_type: str) -> str:
        """Assess risk level of package change"""
        package_lower = package.lower()
        
        # High risk packages
        if any(risk_pkg in package_lower for risk_pkg in self.high_risk_packages):
            return "high"
        
        # Medium risk for security-related packages
        security_keywords = ['auth', 'crypto', 'security', 'ssl', 'tls', 'jwt', 'oauth']
        if any(keyword in package_lower for keyword in security_keywords):
            return "medium"
        
        # Higher risk for downgrades
        if change_type == "downgraded":
            return "medium"
        
        # Default to low risk
        return "low"