"""
Reviewer Agent for generating review checklists and identifying potential issues
"""

from typing import Dict, List, Any
from collections import defaultdict

from app.agents.base import AbstractAgent
from app.models.schemas import PRContext, AgentResult, ReviewChecklistItem
from app.logging import get_logger

logger = get_logger(__name__)


class ReviewerAgent(AbstractAgent):
    """Agent for generating comprehensive review checklists"""
    
    def __init__(self):
        super().__init__("reviewer")
    
    def run(self, ctx: PRContext) -> AgentResult:
        """Run reviewer analysis"""
        logger.info(f"Running {self.name} agent", repo=ctx.repo_full_name, pr=ctx.pr_number)
        
        warnings = []
        checklist_items = []
        
        try:
            # Generate checklist items from various analyses
            checklist_items.extend(self._analyze_code_quality(ctx))
            checklist_items.extend(self._analyze_security_considerations(ctx))
            checklist_items.extend(self._analyze_performance_implications(ctx))
            checklist_items.extend(self._analyze_maintainability(ctx))
            checklist_items.extend(self._analyze_testing_coverage(ctx))
            checklist_items.extend(self._analyze_documentation(ctx))
            checklist_items.extend(self._analyze_breaking_changes(ctx))
            
            # Sort by severity
            checklist_items.sort(key=lambda x: {'high': 0, 'medium': 1, 'low': 2}[x.severity])
            
            payload = {
                "review_checklist": [item.dict() for item in checklist_items],
                "analysis_summary": {
                    "total_items": len(checklist_items),
                    "high_priority": len([item for item in checklist_items if item.severity == 'high']),
                    "medium_priority": len([item for item in checklist_items if item.severity == 'medium']),
                    "low_priority": len([item for item in checklist_items if item.severity == 'low'])
                }
            }
            
            return self._create_result(payload, warnings)
            
        except Exception as e:
            logger.error(f"Error in {self.name} agent", error=str(e), exc_info=True)
            warnings.append(f"Error during review analysis: {str(e)}")
            
            # Return basic checklist
            return self._create_result({
                "review_checklist": [
                    ReviewChecklistItem(
                        category="General",
                        text="Standard code review (automated analysis failed)",
                        severity="medium"
                    ).dict()
                ],
                "analysis_summary": {"error": str(e)}
            }, warnings)
    
    def _analyze_code_quality(self, ctx: PRContext) -> List[ReviewChecklistItem]:
        """Analyze code quality aspects"""
        items = []
        
        # Large functions/files
        large_files = [f for f in ctx.files if f.additions + f.deletions > 300]
        if large_files:
            items.append(ReviewChecklistItem(
                category="Code Quality",
                text=f"Review large changes in {len(large_files)} file(s) for potential refactoring opportunities",
                severity="medium",
                line_reference=", ".join(f.filename for f in large_files[:3])
            ))
        
        # Complex changes
        complex_files = [f for f in ctx.files if f.additions + f.deletions > 100 and 
                        self._has_complex_logic(f.patch if f.patch else "")]
        if complex_files:
            items.append(ReviewChecklistItem(
                category="Code Quality",
                text="Verify complex logic changes are well-structured and readable",
                severity="high",
                line_reference=", ".join(f.filename for f in complex_files[:2])
            ))
        
        # Error handling
        files_with_errors = [f for f in ctx.files if f.patch and 
                           any(keyword in f.patch.lower() for keyword in ['exception', 'error', 'try', 'catch'])]
        if files_with_errors:
            items.append(ReviewChecklistItem(
                category="Code Quality",
                text="Ensure proper error handling and meaningful error messages",
                severity="medium"
            ))
        
        # Code duplication
        if len(ctx.files) > 5:
            items.append(ReviewChecklistItem(
                category="Code Quality",
                text="Check for potential code duplication across multiple files",
                severity="low"
            ))
        
        return items
    
    def _analyze_security_considerations(self, ctx: PRContext) -> List[ReviewChecklistItem]:
        """Analyze security-related considerations"""
        items = []
        
        # Authentication/authorization files
        auth_files = [f for f in ctx.files if self._is_auth_related(f.filename)]
        if auth_files:
            items.append(ReviewChecklistItem(
                category="Security",
                text="Verify authentication and authorization logic is secure and properly tested",
                severity="high",
                line_reference=", ".join(f.filename for f in auth_files)
            ))
        
        # Input validation
        files_with_inputs = [f for f in ctx.files if f.patch and 
                           any(keyword in f.patch.lower() for keyword in ['input', 'request', 'param', 'form'])]
        if files_with_inputs:
            items.append(ReviewChecklistItem(
                category="Security",
                text="Ensure all user inputs are properly validated and sanitized",
                severity="high"
            ))
        
        # Database operations
        db_files = [f for f in ctx.files if f.patch and 
                   any(keyword in f.patch.lower() for keyword in ['sql', 'query', 'database', 'db'])]
        if db_files:
            items.append(ReviewChecklistItem(
                category="Security",
                text="Review database operations for SQL injection vulnerabilities",
                severity="high"
            ))
        
        # Configuration changes
        config_files = [f for f in ctx.files if self._is_config_file(f.filename)]
        if config_files:
            items.append(ReviewChecklistItem(
                category="Security",
                text="Review configuration changes for security implications",
                severity="medium",
                line_reference=", ".join(f.filename for f in config_files)
            ))
        
        return items
    
    def _analyze_performance_implications(self, ctx: PRContext) -> List[ReviewChecklistItem]:
        """Analyze performance implications"""
        items = []
        
        # Database queries
        files_with_queries = [f for f in ctx.files if f.patch and 
                            any(keyword in f.patch.lower() for keyword in ['select', 'join', 'query', 'fetch'])]
        if files_with_queries:
            items.append(ReviewChecklistItem(
                category="Performance",
                text="Review database queries for efficiency and proper indexing",
                severity="medium"
            ))
        
        # Loops and iterations
        files_with_loops = [f for f in ctx.files if f.patch and 
                          any(keyword in f.patch.lower() for keyword in ['for', 'while', 'foreach', 'map', 'filter'])]
        if files_with_loops:
            items.append(ReviewChecklistItem(
                category="Performance",
                text="Check loop implementations for performance efficiency",
                severity="low"
            ))
        
        # API calls
        files_with_api = [f for f in ctx.files if f.patch and 
                         any(keyword in f.patch.lower() for keyword in ['http', 'request', 'api', 'fetch', 'call'])]
        if files_with_api:
            items.append(ReviewChecklistItem(
                category="Performance",
                text="Ensure API calls are optimized and have proper timeout/retry logic",
                severity="medium"
            ))
        
        # Large file additions
        large_additions = sum(f.additions for f in ctx.files)
        if large_additions > 1000:
            items.append(ReviewChecklistItem(
                category="Performance",
                text=f"Large code addition ({large_additions} lines) - consider performance impact",
                severity="low"
            ))
        
        return items
    
    def _analyze_maintainability(self, ctx: PRContext) -> List[ReviewChecklistItem]:
        """Analyze maintainability aspects"""
        items = []
        
        # New dependencies
        if ctx.dependency_files:
            items.append(ReviewChecklistItem(
                category="Maintainability",
                text="Review new dependencies for necessity and long-term maintenance",
                severity="medium"
            ))
        
        # Code organization
        if len(ctx.files) > 10:
            items.append(ReviewChecklistItem(
                category="Maintainability",
                text="Ensure changes maintain good code organization and separation of concerns",
                severity="low"
            ))
        
        # Comments and documentation
        code_files = [f for f in ctx.files if self._is_code_file(f.filename)]
        if len(code_files) > 3:
            items.append(ReviewChecklistItem(
                category="Maintainability",
                text="Verify complex code sections have appropriate comments and documentation",
                severity="low"
            ))
        
        return items
    
    def _analyze_testing_coverage(self, ctx: PRContext) -> List[ReviewChecklistItem]:
        """Analyze testing coverage"""
        items = []
        
        # Test files ratio
        test_files = [f for f in ctx.files if self._is_test_file(f.filename)]
        code_files = [f for f in ctx.files if self._is_code_file(f.filename) and not self._is_test_file(f.filename)]
        
        if code_files and not test_files:
            items.append(ReviewChecklistItem(
                category="Testing",
                text="No test files modified - ensure adequate test coverage for new/changed code",
                severity="medium"
            ))
        elif test_files and len(test_files) < len(code_files) / 2:
            items.append(ReviewChecklistItem(
                category="Testing",
                text="Consider adding more test coverage for the modified code",
                severity="low"
            ))
        
        # Critical functionality testing
        critical_files = [f for f in ctx.files if self._is_critical_functionality(f.filename)]
        if critical_files:
            items.append(ReviewChecklistItem(
                category="Testing",
                text="Ensure critical functionality changes have comprehensive test coverage",
                severity="high",
                line_reference=", ".join(f.filename for f in critical_files)
            ))
        
        return items
    
    def _analyze_documentation(self, ctx: PRContext) -> List[ReviewChecklistItem]:
        """Analyze documentation needs"""
        items = []
        
        # API changes
        api_files = [f for f in ctx.files if self._is_api_file(f.filename)]
        if api_files:
            items.append(ReviewChecklistItem(
                category="Documentation",
                text="Update API documentation for any interface changes",
                severity="medium",
                line_reference=", ".join(f.filename for f in api_files)
            ))
        
        # Public interface changes
        if any(f.filename.endswith('.py') and f.patch and 'def ' in f.patch for f in ctx.files):
            items.append(ReviewChecklistItem(
                category="Documentation",
                text="Ensure public functions have appropriate docstrings",
                severity="low"
            ))
        
        # README or docs changes needed
        readme_changed = any('readme' in f.filename.lower() for f in ctx.files)
        if not readme_changed and len([f for f in ctx.files if self._is_code_file(f.filename)]) > 5:
            items.append(ReviewChecklistItem(
                category="Documentation",
                text="Consider updating README or documentation for significant changes",
                severity="low"
            ))
        
        return items
    
    def _analyze_breaking_changes(self, ctx: PRContext) -> List[ReviewChecklistItem]:
        """Analyze potential breaking changes"""
        items = []
        
        # Function signature changes
        functions_removed = []
        for file in ctx.files:
            if file.patch and file.filename.endswith(('.py', '.js', '.ts', '.java')):
                removed_lines = [line for line in file.patch.split('\n') if line.startswith('-')]
                for line in removed_lines:
                    if 'def ' in line or 'function ' in line or 'class ' in line:
                        functions_removed.append(file.filename)
                        break
        
        if functions_removed:
            items.append(ReviewChecklistItem(
                category="Breaking Changes",
                text="Verify removed/modified functions don't break existing functionality",
                severity="high",
                line_reference=", ".join(functions_removed)
            ))
        
        # Database schema changes
        migration_files = [f for f in ctx.files if 'migration' in f.filename.lower() or '.sql' in f.filename.lower()]
        if migration_files:
            items.append(ReviewChecklistItem(
                category="Breaking Changes",
                text="Review database migrations for backward compatibility",
                severity="high",
                line_reference=", ".join(f.filename for f in migration_files)
            ))
        
        # Configuration changes
        config_files = [f for f in ctx.files if self._is_config_file(f.filename)]
        if config_files:
            items.append(ReviewChecklistItem(
                category="Breaking Changes",
                text="Ensure configuration changes maintain backward compatibility",
                severity="medium"
            ))
        
        return items
    
    def _has_complex_logic(self, patch: str) -> bool:
        """Check if patch contains complex logic"""
        if not patch:
            return False
        
        complexity_indicators = [
            'if', 'else', 'elif', 'switch', 'case',
            'for', 'while', 'foreach',
            'try', 'catch', 'except',
            'async', 'await', 'promise'
        ]
        
        lines = patch.split('\n')
        complex_lines = sum(1 for line in lines if 
                          any(indicator in line.lower() for indicator in complexity_indicators))
        
        return complex_lines > 5 or len(lines) > 50
    
    def _is_auth_related(self, filename: str) -> bool:
        """Check if file is authentication/authorization related"""
        auth_patterns = ['auth', 'login', 'signin', 'permission', 'role', 'access', 'security']
        return any(pattern in filename.lower() for pattern in auth_patterns)
    
    def _is_config_file(self, filename: str) -> bool:
        """Check if file is a configuration file"""
        config_patterns = ['.env', '.ini', '.conf', '.config', 'settings', '.yml', '.yaml']
        return any(pattern in filename.lower() for pattern in config_patterns)
    
    def _is_code_file(self, filename: str) -> bool:
        """Check if file is a code file"""
        code_extensions = ['.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c', '.rb', '.php']
        return any(filename.endswith(ext) for ext in code_extensions)
    
    def _is_test_file(self, filename: str) -> bool:
        """Check if file is a test file"""
        test_patterns = ['test_', '_test.', 'tests/', 'spec_', '_spec.', '__tests__/']
        return any(pattern in filename.lower() for pattern in test_patterns)
    
    def _is_critical_functionality(self, filename: str) -> bool:
        """Check if file contains critical functionality"""
        critical_patterns = ['core', 'main', 'critical', 'essential', 'payment', 'auth', 'security']
        return any(pattern in filename.lower() for pattern in critical_patterns)
    
    def _is_api_file(self, filename: str) -> bool:
        """Check if file contains API definitions"""
        api_patterns = ['api', 'endpoint', 'route', 'controller', 'handler', 'view']
        return any(pattern in filename.lower() for pattern in api_patterns)