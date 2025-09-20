"""
Repository Scanner Agent for analyzing code changes
"""

from typing import Dict, List, Any
import re
from collections import defaultdict

from app.agents.base import AbstractAgent
from app.models.schemas import PRContext, AgentResult
from app.services.diff_parser import DiffParser
from app.logging import get_logger

logger = get_logger(__name__)


class RepoScannerAgent(AbstractAgent):
    """Agent for scanning repository changes and generating summaries"""
    
    def __init__(self):
        super().__init__("repo_scanner")
        self.diff_parser = DiffParser()
    
    def run(self, ctx: PRContext) -> AgentResult:
        """Run repository scanning analysis"""
        logger.info(f"Running {self.name} agent", repo=ctx.repo_full_name, pr=ctx.pr_number)
        
        warnings = []
        
        try:
            # Parse diff for detailed analysis
            diff_analysis = self.diff_parser.parse_diff(ctx.raw_diff)
            
            # Generate summary
            summary = self._generate_summary(ctx, diff_analysis)
            
            # Categorize changes into changelog
            changelog = self._categorize_changes(ctx)
            
            # Identify complexity flags
            complexity_flags = self._identify_complexity_flags(ctx, diff_analysis)
            
            payload = {
                "summary": summary,
                "changelog": changelog,
                "complexity_flags": complexity_flags,
                "diff_stats": {
                    "total_files": len(ctx.files),
                    "total_additions": sum(f.additions for f in ctx.files),
                    "total_deletions": sum(f.deletions for f in ctx.files),
                    "language_distribution": ctx.language_stats
                },
                "hotspots": diff_analysis.get("hotspots", [])
            }
            
            return self._create_result(payload, warnings)
            
        except Exception as e:
            logger.error(f"Error in {self.name} agent", error=str(e), exc_info=True)
            warnings.append(f"Error during repository scanning: {str(e)}")
            
            # Return minimal result
            return self._create_result({
                "summary": "Error occurred during analysis",
                "changelog": {},
                "complexity_flags": [],
                "diff_stats": {
                    "total_files": len(ctx.files),
                    "total_additions": sum(f.additions for f in ctx.files),
                    "total_deletions": sum(f.deletions for f in ctx.files)
                }
            }, warnings)
    
    def _generate_summary(self, ctx: PRContext, diff_analysis: Dict) -> str:
        """Generate high-level summary of changes"""
        total_files = len(ctx.files)
        total_additions = sum(f.additions for f in ctx.files)
        total_deletions = sum(f.deletions for f in ctx.files)
        
        # Identify primary language
        primary_lang = max(ctx.language_stats.items(), key=lambda x: x[1])[0] if ctx.language_stats else "Unknown"
        
        # Basic categorization based on file patterns
        file_types = defaultdict(int)
        for file in ctx.files:
            if self._is_test_file(file.filename):
                file_types['test'] += 1
            elif self._is_config_file(file.filename):
                file_types['config'] += 1
            elif self._is_doc_file(file.filename):
                file_types['documentation'] += 1
            else:
                file_types['code'] += 1
        
        # Generate descriptive summary
        summary_parts = []
        
        if total_files == 1:
            summary_parts.append(f"Modifies 1 {primary_lang} file")
        else:
            summary_parts.append(f"Modifies {total_files} files")
        
        if total_additions > 0 and total_deletions > 0:
            summary_parts.append(f"with {total_additions} additions and {total_deletions} deletions")
        elif total_additions > 0:
            summary_parts.append(f"adding {total_additions} lines")
        elif total_deletions > 0:
            summary_parts.append(f"removing {total_deletions} lines")
        
        # Add file type context
        if file_types['test'] > 0:
            summary_parts.append(f"including {file_types['test']} test file(s)")
        
        if file_types['config'] > 0:
            summary_parts.append(f"and {file_types['config']} configuration file(s)")
        
        summary = ". ".join(summary_parts) + "."
        
        # Add context from PR title if available
        if ctx.pr_title:
            title_lower = ctx.pr_title.lower()
            if any(keyword in title_lower for keyword in ['fix', 'bug', 'issue']):
                summary = f"Bug fix: {summary}"
            elif any(keyword in title_lower for keyword in ['feature', 'add', 'implement']):
                summary = f"Feature addition: {summary}"
            elif any(keyword in title_lower for keyword in ['refactor', 'cleanup', 'reorganize']):
                summary = f"Refactoring: {summary}"
            elif any(keyword in title_lower for keyword in ['update', 'upgrade']):
                summary = f"Update: {summary}"
        
        return summary
    
    def _categorize_changes(self, ctx: PRContext) -> Dict[str, List[str]]:
        """Categorize changes into changelog buckets"""
        changelog = {
            "features": [],
            "fixes": [],
            "refactors": [],
            "docs": [],
            "tests": []
        }
        
        # Analyze PR title and body for keywords
        pr_text = f"{ctx.pr_title} {ctx.pr_body or ''}".lower()
        
        # Feature indicators
        if any(keyword in pr_text for keyword in ['add', 'implement', 'feature', 'new']):
            changelog["features"].append(f"Added new functionality based on PR title: {ctx.pr_title}")
        
        # Bug fix indicators
        if any(keyword in pr_text for keyword in ['fix', 'bug', 'issue', 'resolve']):
            changelog["fixes"].append(f"Fixed issue: {ctx.pr_title}")
        
        # Refactoring indicators
        if any(keyword in pr_text for keyword in ['refactor', 'cleanup', 'reorganize', 'improve']):
            changelog["refactors"].append(f"Code refactoring: {ctx.pr_title}")
        
        # Analyze files for additional context
        for file in ctx.files:
            filename = file.filename.lower()
            
            if self._is_test_file(filename):
                if file.status.value == "added":
                    changelog["tests"].append(f"Added test file: {file.filename}")
                elif file.additions > file.deletions:
                    changelog["tests"].append(f"Enhanced tests in: {file.filename}")
            
            elif self._is_doc_file(filename):
                if file.status.value == "added":
                    changelog["docs"].append(f"Added documentation: {file.filename}")
                elif file.additions > 0:
                    changelog["docs"].append(f"Updated documentation: {file.filename}")
            
            elif file.status.value == "added" and self._is_code_file(filename):
                changelog["features"].append(f"Added new file: {file.filename}")
        
        # Remove empty categories
        return {k: v for k, v in changelog.items() if v}
    
    def _identify_complexity_flags(self, ctx: PRContext, diff_analysis: Dict) -> List[str]:
        """Identify complexity and risk flags"""
        flags = []
        
        total_changes = sum(f.additions + f.deletions for f in ctx.files)
        
        # Large change flags
        if total_changes > 1000:
            flags.append(f"Very large change: {total_changes} total lines modified")
        elif total_changes > 500:
            flags.append(f"Large change: {total_changes} total lines modified")
        
        # Single file with many changes
        for file in ctx.files:
            file_changes = file.additions + file.deletions
            if file_changes > 300:
                flags.append(f"Large single file change: {file.filename} ({file_changes} lines)")
        
        # Many files changed
        if len(ctx.files) > 20:
            flags.append(f"Many files changed: {len(ctx.files)} files")
        elif len(ctx.files) > 10:
            flags.append(f"Multiple files changed: {len(ctx.files)} files")
        
        # Binary files
        binary_files = [f for f in ctx.files if self._is_binary_file(f.filename)]
        if binary_files:
            flags.append(f"Binary files changed: {len(binary_files)} files")
        
        # Critical system files
        critical_files = [f for f in ctx.files if self._is_critical_file(f.filename)]
        if critical_files:
            flags.append(f"Critical system files modified: {', '.join(f.filename for f in critical_files)}")
        
        # Hotspots from diff analysis
        hotspots = diff_analysis.get("hotspots", [])
        if hotspots:
            flags.append(f"Code hotspots detected: {len(hotspots)} files with high complexity")
        
        return flags
    
    def _is_test_file(self, filename: str) -> bool:
        """Check if file is a test file"""
        test_patterns = [
            'test_', '_test.', 'tests/', '/test/', '.test.', 
            'spec_', '_spec.', 'specs/', '/spec/',
            '.spec.', '__tests__/', '/*.test.*'
        ]
        return any(pattern in filename.lower() for pattern in test_patterns)
    
    def _is_config_file(self, filename: str) -> bool:
        """Check if file is a configuration file"""
        config_files = [
            'config.', 'settings.', '.env', '.ini', '.conf',
            'docker', 'makefile', '.yml', '.yaml', '.json',
            'requirements.txt', 'package.json', 'setup.py',
            'pyproject.toml', 'cargo.toml'
        ]
        return any(pattern in filename.lower() for pattern in config_files)
    
    def _is_doc_file(self, filename: str) -> bool:
        """Check if file is documentation"""
        doc_extensions = ['.md', '.rst', '.txt', '.pdf', '.doc', '.docx']
        doc_dirs = ['docs/', 'doc/', 'documentation/']
        
        return (any(filename.lower().endswith(ext) for ext in doc_extensions) or
                any(dir_name in filename.lower() for dir_name in doc_dirs))
    
    def _is_code_file(self, filename: str) -> bool:
        """Check if file is a code file"""
        code_extensions = [
            '.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c',
            '.rb', '.php', '.swift', '.kt', '.scala', '.cs'
        ]
        return any(filename.lower().endswith(ext) for ext in code_extensions)
    
    def _is_binary_file(self, filename: str) -> bool:
        """Check if file is binary"""
        binary_extensions = [
            '.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip', '.tar', '.gz',
            '.exe', '.dll', '.so', '.dylib', '.bin'
        ]
        return any(filename.lower().endswith(ext) for ext in binary_extensions)
    
    def _is_critical_file(self, filename: str) -> bool:
        """Check if file is critical system file"""
        critical_patterns = [
            'dockerfile', 'docker-compose', '.github/workflows/',
            'security', 'auth', 'login', 'password', 'secret',
            'deploy', 'production', 'database', 'migration'
        ]
        return any(pattern in filename.lower() for pattern in critical_patterns)