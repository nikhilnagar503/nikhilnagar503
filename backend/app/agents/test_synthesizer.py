"""
Test Synthesizer Agent for generating test suggestions
"""

from typing import Dict, List, Any
import re

from app.agents.base import AbstractAgent
from app.models.schemas import PRContext, AgentResult, TestSuggestion
from app.services.diff_parser import DiffParser
from app.logging import get_logger

logger = get_logger(__name__)


class TestSynthesizerAgent(AbstractAgent):
    """Agent for synthesizing test suggestions based on code changes"""
    
    def __init__(self):
        super().__init__("test_synthesizer")
        self.diff_parser = DiffParser()
        
        # Function patterns for different languages
        self.function_patterns = {
            'py': r'^\s*def\s+(\w+)\s*\(',
            'js': r'^\s*(?:function\s+(\w+)|(\w+)\s*[:=]\s*(?:function|\([^)]*\)\s*=>))',
            'java': r'^\s*(?:public|private|protected)?\s*(?:static\s+)?(?:\w+\s+)*(\w+)\s*\(',
            'go': r'^\s*func\s+(\w+)\s*\(',
            'rs': r'^\s*(?:pub\s+)?fn\s+(\w+)\s*\('
        }
    
    def run(self, ctx: PRContext) -> AgentResult:
        """Run test synthesis analysis"""
        logger.info(f"Running {self.name} agent", repo=ctx.repo_full_name, pr=ctx.pr_number)
        
        warnings = []
        test_suggestions = []
        
        try:
            # Analyze each changed file for test opportunities
            for file in ctx.files:
                if self._is_testable_file(file.filename):
                    file_suggestions = self._analyze_file_for_tests(file, ctx)
                    test_suggestions.extend(file_suggestions)
            
            # Remove duplicates and limit suggestions
            test_suggestions = self._deduplicate_suggestions(test_suggestions)
            test_suggestions = test_suggestions[:20]  # Limit to 20 suggestions
            
            payload = {
                "test_suggestions": [s.dict() for s in test_suggestions],
                "analysis_summary": {
                    "total_suggestions": len(test_suggestions),
                    "files_analyzed": len([f for f in ctx.files if self._is_testable_file(f.filename)]),
                    "functions_identified": len(set(s.function_name for s in test_suggestions if s.function_name))
                }
            }
            
            return self._create_result(payload, warnings)
            
        except Exception as e:
            logger.error(f"Error in {self.name} agent", error=str(e), exc_info=True)
            warnings.append(f"Error during test synthesis: {str(e)}")
            
            return self._create_result({
                "test_suggestions": [],
                "analysis_summary": {"error": str(e)}
            }, warnings)
    
    def _analyze_file_for_tests(self, file, ctx: PRContext) -> List[TestSuggestion]:
        """Analyze a file for test suggestions"""
        suggestions = []
        
        if not file.patch:
            return suggestions
        
        # Extract file extension
        ext = file.filename.split('.')[-1] if '.' in file.filename else ''
        
        # Find functions in the patch
        functions = self._extract_functions_from_patch(file.patch, ext)
        
        # Generate suggestions for each function
        for function_info in functions:
            function_name = function_info['name']
            change_type = function_info['change_type']
            
            # Generate different types of test suggestions
            suggestions.extend(self._generate_function_test_suggestions(
                file.filename, function_name, change_type, function_info.get('line', '')
            ))
        
        # Generate file-level suggestions
        if file.status.value == "added":
            suggestions.append(TestSuggestion(
                target_file=file.filename,
                test_type="integration",
                description=f"Integration tests for new file {file.filename}",
                rationale="New files should have comprehensive test coverage",
                sample_stub=f"test_{file.filename.replace('.', '_').replace('/', '_')}_integration()"
            ))
        
        # Check for specific patterns that need testing
        if file.patch:
            suggestions.extend(self._analyze_patch_patterns(file.filename, file.patch))
        
        return suggestions
    
    def _extract_functions_from_patch(self, patch: str, ext: str) -> List[Dict[str, str]]:
        """Extract function information from patch"""
        functions = []
        pattern = self.function_patterns.get(ext)
        
        if not pattern:
            return functions
        
        lines = patch.split('\n')
        for line in lines:
            if line.startswith('+') or line.startswith('-'):
                change_type = 'added' if line.startswith('+') else 'removed'
                content = line[1:]
                
                match = re.search(pattern, content)
                if match:
                    function_name = match.group(1) or match.group(2)  # Handle multiple capture groups
                    if function_name and not function_name.startswith('_'):  # Skip private functions
                        functions.append({
                            'name': function_name,
                            'change_type': change_type,
                            'line': content.strip()
                        })
        
        return functions
    
    def _generate_function_test_suggestions(self, filename: str, function_name: str, 
                                          change_type: str, function_line: str) -> List[TestSuggestion]:
        """Generate test suggestions for a specific function"""
        suggestions = []
        
        # Positive test case
        suggestions.append(TestSuggestion(
            target_file=filename,
            function_name=function_name,
            test_type="positive",
            description=f"Test {function_name} with valid inputs",
            rationale="Ensure function works correctly with expected inputs",
            sample_stub=f"test_{function_name}_valid_input()"
        ))
        
        # Negative test case
        suggestions.append(TestSuggestion(
            target_file=filename,
            function_name=function_name,
            test_type="negative",
            description=f"Test {function_name} with invalid inputs",
            rationale="Verify proper error handling for invalid inputs",
            sample_stub=f"test_{function_name}_invalid_input()"
        ))
        
        # Edge case suggestions based on function signature/content
        if self._has_numeric_parameters(function_line):
            suggestions.append(TestSuggestion(
                target_file=filename,
                function_name=function_name,
                test_type="boundary",
                description=f"Test {function_name} with boundary values",
                rationale="Numeric parameters should be tested with min/max/zero values",
                sample_stub=f"test_{function_name}_boundary_values()"
            ))
        
        if self._has_string_parameters(function_line):
            suggestions.append(TestSuggestion(
                target_file=filename,
                function_name=function_name,
                test_type="boundary",
                description=f"Test {function_name} with empty/null strings",
                rationale="String parameters should be tested with empty and null values",
                sample_stub=f"test_{function_name}_empty_strings()"
            ))
        
        if self._has_collection_parameters(function_line):
            suggestions.append(TestSuggestion(
                target_file=filename,
                function_name=function_name,
                test_type="boundary",
                description=f"Test {function_name} with empty collections",
                rationale="Collection parameters should be tested with empty lists/arrays",
                sample_stub=f"test_{function_name}_empty_collections()"
            ))
        
        return suggestions
    
    def _analyze_patch_patterns(self, filename: str, patch: str) -> List[TestSuggestion]:
        """Analyze patch for specific patterns that need testing"""
        suggestions = []
        
        # Look for error handling patterns
        if any(keyword in patch.lower() for keyword in ['try:', 'except:', 'catch', 'throw', 'error']):
            suggestions.append(TestSuggestion(
                target_file=filename,
                test_type="negative",
                description="Test error handling and exception cases",
                rationale="Code contains error handling that should be tested",
                sample_stub="test_error_handling()"
            ))
        
        # Look for database operations
        if any(keyword in patch.lower() for keyword in ['select', 'insert', 'update', 'delete', 'query']):
            suggestions.append(TestSuggestion(
                target_file=filename,
                test_type="integration",
                description="Test database operations with mocked/test database",
                rationale="Database operations require integration testing",
                sample_stub="test_database_operations()"
            ))
        
        # Look for API calls
        if any(keyword in patch.lower() for keyword in ['request', 'response', 'api', 'http', 'fetch']):
            suggestions.append(TestSuggestion(
                target_file=filename,
                test_type="integration",
                description="Test API interactions with mocked responses",
                rationale="External API calls should be tested with mocked responses",
                sample_stub="test_api_interactions()"
            ))
        
        # Look for file operations
        if any(keyword in patch.lower() for keyword in ['file', 'read', 'write', 'open', 'save']):
            suggestions.append(TestSuggestion(
                target_file=filename,
                test_type="integration",
                description="Test file operations with temporary files",
                rationale="File operations should be tested with controlled file system state",
                sample_stub="test_file_operations()"
            ))
        
        # Look for validation logic
        if any(keyword in patch.lower() for keyword in ['validate', 'check', 'verify', 'assert']):
            suggestions.append(TestSuggestion(
                target_file=filename,
                test_type="positive",
                description="Test validation logic with various input scenarios",
                rationale="Validation logic requires comprehensive input testing",
                sample_stub="test_validation_logic()"
            ))
        
        return suggestions
    
    def _has_numeric_parameters(self, function_line: str) -> bool:
        """Check if function likely has numeric parameters"""
        numeric_hints = ['int', 'float', 'number', 'count', 'size', 'length', 'index']
        return any(hint in function_line.lower() for hint in numeric_hints)
    
    def _has_string_parameters(self, function_line: str) -> bool:
        """Check if function likely has string parameters"""
        string_hints = ['str', 'string', 'text', 'name', 'message', 'path']
        return any(hint in function_line.lower() for hint in string_hints)
    
    def _has_collection_parameters(self, function_line: str) -> bool:
        """Check if function likely has collection parameters"""
        collection_hints = ['list', 'array', 'dict', 'map', 'set', 'collection']
        return any(hint in function_line.lower() for hint in collection_hints)
    
    def _is_testable_file(self, filename: str) -> bool:
        """Check if file is suitable for test generation"""
        # Skip test files themselves
        if self._is_test_file(filename):
            return False
        
        # Skip non-code files
        code_extensions = ['.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c']
        if not any(filename.endswith(ext) for ext in code_extensions):
            return False
        
        # Skip configuration and documentation files
        skip_patterns = ['config', 'settings', '__init__', 'migrations/', 'docs/']
        if any(pattern in filename.lower() for pattern in skip_patterns):
            return False
        
        return True
    
    def _is_test_file(self, filename: str) -> bool:
        """Check if file is already a test file"""
        test_patterns = ['test_', '_test.', 'tests/', 'spec_', '_spec.', '__tests__/']
        return any(pattern in filename.lower() for pattern in test_patterns)
    
    def _deduplicate_suggestions(self, suggestions: List[TestSuggestion]) -> List[TestSuggestion]:
        """Remove duplicate test suggestions"""
        seen = set()
        unique_suggestions = []
        
        for suggestion in suggestions:
            # Create a key for deduplication
            key = (suggestion.target_file, suggestion.function_name, 
                  suggestion.test_type, suggestion.description)
            
            if key not in seen:
                seen.add(key)
                unique_suggestions.append(suggestion)
        
        return unique_suggestions