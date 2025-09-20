"""
Secret scanning utilities for detecting secrets in code
"""

import re
from typing import List, Dict, Tuple
from app.models.schemas import SecretDetection
from app.logging import get_logger

logger = get_logger(__name__)


class SecretScanner:
    """Scanner for detecting secrets and sensitive information in code"""
    
    def __init__(self):
        self.patterns = {
            'aws_access_key': {
                'pattern': r'AKIA[0-9A-Z]{16}',
                'description': 'AWS Access Key ID'
            },
            'aws_secret_key': {
                'pattern': r'[A-Za-z0-9/+=]{40}',
                'description': 'AWS Secret Access Key'
            },
            'github_token': {
                'pattern': r'gh[pousr]_[A-Za-z0-9_]{36,255}',
                'description': 'GitHub Token'
            },
            'slack_token': {
                'pattern': r'xox[baprs]-([0-9a-zA-Z]{10,48})',
                'description': 'Slack Token'
            },
            'private_key': {
                'pattern': r'-----BEGIN [A-Z]+ PRIVATE KEY-----',
                'description': 'Private Key'
            },
            'api_key': {
                'pattern': r'(?i)api[_-]?key[\'"\s]*[:=][\'"\s]*[0-9a-zA-Z_\-]{16,128}',
                'description': 'Generic API Key'
            },
            'password': {
                'pattern': r'(?i)password[\'"\s]*[:=][\'"\s]*[0-9a-zA-Z_\-!@#$%^&*()]{8,128}',
                'description': 'Password'
            },
            'jwt_token': {
                'pattern': r'eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*',
                'description': 'JWT Token'
            },
            'database_url': {
                'pattern': r'(?i)(postgres|mysql|mongodb)://[a-zA-Z0-9_.-]+:[a-zA-Z0-9_.-]+@[a-zA-Z0-9_.-]+',
                'description': 'Database Connection String'
            },
            'email_credentials': {
                'pattern': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}:[a-zA-Z0-9_\-!@#$%^&*()]{6,}',
                'description': 'Email with Password'
            }
        }
        
        # Compiled patterns for better performance
        self.compiled_patterns = {
            name: re.compile(pattern['pattern'])
            for name, pattern in self.patterns.items()
        }
    
    def scan_content(self, content: str, filename: str) -> List[SecretDetection]:
        """
        Scan content for secrets
        
        Args:
            content: File content to scan
            filename: Name of the file being scanned
            
        Returns:
            List of detected secrets
        """
        detections = []
        
        # Skip binary files and large files
        if self._is_binary_file(filename) or len(content) > 1000000:
            return detections
        
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # Skip comments and certain safe contexts
            if self._is_safe_line(line, filename):
                continue
            
            for pattern_name, compiled_pattern in self.compiled_patterns.items():
                matches = compiled_pattern.finditer(line)
                
                for match in matches:
                    # Additional validation to reduce false positives
                    if self._validate_detection(pattern_name, match.group(), line, filename):
                        detection = SecretDetection(
                            pattern_type=self.patterns[pattern_name]['description'],
                            filename=filename,
                            line_number=line_num,
                            severity=self._get_severity(pattern_name)
                        )
                        detections.append(detection)
        
        return detections
    
    def scan_diff(self, diff_content: str, filename: str) -> List[SecretDetection]:
        """
        Scan diff content for secrets in added lines
        
        Args:
            diff_content: Diff content to scan
            filename: Name of the file
            
        Returns:
            List of detected secrets in added lines
        """
        detections = []
        
        if self._is_binary_file(filename):
            return detections
        
        lines = diff_content.split('\n')
        line_num = 0
        
        for line in lines:
            if line.startswith('@@'):
                # Extract line number from hunk header
                match = re.search(r'\+(\d+)', line)
                if match:
                    line_num = int(match.group(1)) - 1
                continue
            
            if line.startswith('+') and not line.startswith('+++'):
                line_num += 1
                content = line[1:]  # Remove '+' prefix
                
                if self._is_safe_line(content, filename):
                    continue
                
                for pattern_name, compiled_pattern in self.compiled_patterns.items():
                    matches = compiled_pattern.finditer(content)
                    
                    for match in matches:
                        if self._validate_detection(pattern_name, match.group(), content, filename):
                            detection = SecretDetection(
                                pattern_type=self.patterns[pattern_name]['description'],
                                filename=filename,
                                line_number=line_num,
                                severity=self._get_severity(pattern_name)
                            )
                            detections.append(detection)
            elif not line.startswith('-'):
                line_num += 1
        
        return detections
    
    def _is_binary_file(self, filename: str) -> bool:
        """Check if file is likely binary"""
        binary_extensions = {
            '.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip', '.tar', '.gz',
            '.exe', '.dll', '.so', '.dylib', '.bin', '.dat', '.db'
        }
        
        return any(filename.lower().endswith(ext) for ext in binary_extensions)
    
    def _is_safe_line(self, line: str, filename: str) -> bool:
        """Check if line is in a safe context (comments, docs, etc.)"""
        line = line.strip()
        
        # Empty lines
        if not line:
            return True
        
        # Comments
        if filename.endswith('.py') and line.startswith('#'):
            return True
        if filename.endswith(('.js', '.ts', '.java', '.go', '.c', '.cpp')) and line.startswith('//'):
            return True
        if line.startswith('/*') or line.startswith('*') or line.startswith('*/'):
            return True
        
        # Documentation
        if filename.endswith('.md') or filename.endswith('.rst'):
            return True
        
        # Example/test data markers
        safe_markers = [
            'example', 'test', 'mock', 'fake', 'dummy', 'placeholder',
            'YOUR_API_KEY', 'INSERT_KEY_HERE', 'REPLACE_WITH',
            'xxx', 'yyy', 'zzz'
        ]
        
        line_lower = line.lower()
        return any(marker in line_lower for marker in safe_markers)
    
    def _validate_detection(self, pattern_name: str, match: str, line: str, filename: str) -> bool:
        """Additional validation to reduce false positives"""
        
        # Skip very common false positives
        false_positives = [
            'password123', 'apikey123', 'secret123',
            'your_api_key', 'your_password', 'your_secret'
        ]
        
        if match.lower() in false_positives:
            return False
        
        # AWS Secret Key additional validation
        if pattern_name == 'aws_secret_key':
            # Must contain both upper and lower case and numbers
            if not (any(c.isupper() for c in match) and 
                   any(c.islower() for c in match) and 
                   any(c.isdigit() for c in match)):
                return False
        
        # JWT token validation
        if pattern_name == 'jwt_token':
            parts = match.split('.')
            if len(parts) != 3:
                return False
        
        # Skip if in test files with obvious test patterns
        if 'test' in filename.lower():
            test_patterns = ['test_', 'mock_', 'fake_', 'example_']
            if any(pattern in match.lower() for pattern in test_patterns):
                return False
        
        return True
    
    def _get_severity(self, pattern_name: str) -> str:
        """Get severity level for pattern type"""
        high_severity = [
            'aws_access_key', 'aws_secret_key', 'private_key', 
            'database_url', 'github_token'
        ]
        
        if pattern_name in high_severity:
            return 'high'
        else:
            return 'medium'
    
    def get_pattern_summary(self) -> Dict[str, str]:
        """Get summary of all patterns"""
        return {name: pattern['description'] for name, pattern in self.patterns.items()}