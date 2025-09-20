"""
Diff parsing utilities for code analysis
"""

import re
from typing import Dict, List, Tuple, Optional
from app.logging import get_logger

logger = get_logger(__name__)


class DiffParser:
    """Parser for Git diff content"""
    
    def __init__(self):
        self.function_patterns = {
            'python': r'^\s*def\s+(\w+)\s*\(',
            'javascript': r'^\s*(?:function\s+(\w+)|(\w+)\s*[:=]\s*(?:function|\([^)]*\)\s*=>))',
            'java': r'^\s*(?:public|private|protected)?\s*(?:static\s+)?(?:\w+\s+)*(\w+)\s*\(',
            'go': r'^\s*func\s+(\w+)\s*\(',
            'rust': r'^\s*(?:pub\s+)?fn\s+(\w+)\s*\(',
            'cpp': r'^\s*(?:\w+\s+)*(\w+)\s*\([^)]*\)\s*\{',
            'c': r'^\s*(?:\w+\s+)*(\w+)\s*\([^)]*\)\s*\{'
        }
    
    def parse_diff(self, diff_content: str) -> Dict[str, any]:
        """
        Parse diff content to extract useful information
        
        Args:
            diff_content: Raw diff string
            
        Returns:
            Dictionary with parsed diff information
        """
        lines = diff_content.split('\n')
        
        files_changed = []
        total_additions = 0
        total_deletions = 0
        current_file = None
        
        for line in lines:
            if line.startswith('diff --git'):
                # New file
                file_match = re.search(r'diff --git a/(.*?) b/(.*?)$', line)
                if file_match:
                    current_file = {
                        'filename': file_match.group(2),
                        'additions': 0,
                        'deletions': 0,
                        'functions_changed': [],
                        'large_changes': False
                    }
                    files_changed.append(current_file)
            
            elif line.startswith('@@') and current_file:
                # Hunk header - extract line numbers
                hunk_match = re.search(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
                if hunk_match:
                    current_file['hunk_info'] = hunk_match.groups()
            
            elif line.startswith('+') and not line.startswith('+++') and current_file:
                # Addition
                current_file['additions'] += 1
                total_additions += 1
                
                # Check for function definitions
                self._check_function_change(line[1:], current_file, 'added')
            
            elif line.startswith('-') and not line.startswith('---') and current_file:
                # Deletion
                current_file['deletions'] += 1
                total_deletions += 1
                
                # Check for function definitions
                self._check_function_change(line[1:], current_file, 'removed')
        
        # Mark files with large changes
        for file_info in files_changed:
            total_changes = file_info['additions'] + file_info['deletions']
            if total_changes > 100:
                file_info['large_changes'] = True
        
        return {
            'files_changed': files_changed,
            'total_additions': total_additions,
            'total_deletions': total_deletions,
            'total_files': len(files_changed),
            'large_files': [f for f in files_changed if f['large_changes']],
            'hotspots': self._identify_hotspots(files_changed)
        }
    
    def _check_function_change(self, line: str, file_info: Dict, change_type: str):
        """Check if line contains a function definition"""
        filename = file_info['filename']
        ext = filename.split('.')[-1] if '.' in filename else ''
        
        pattern = self.function_patterns.get(ext)
        if pattern:
            match = re.search(pattern, line)
            if match:
                function_name = match.group(1)
                if function_name and function_name not in [f['name'] for f in file_info['functions_changed']]:
                    file_info['functions_changed'].append({
                        'name': function_name,
                        'change_type': change_type,
                        'line': line.strip()
                    })
    
    def _identify_hotspots(self, files_changed: List[Dict]) -> List[Dict]:
        """Identify files that are hotspots (large changes, many functions)"""
        hotspots = []
        
        for file_info in files_changed:
            total_changes = file_info['additions'] + file_info['deletions']
            functions_count = len(file_info['functions_changed'])
            
            risk_score = 0
            reasons = []
            
            if total_changes > 200:
                risk_score += 3
                reasons.append(f"Large change ({total_changes} lines)")
            elif total_changes > 100:
                risk_score += 2
                reasons.append(f"Medium change ({total_changes} lines)")
            
            if functions_count > 5:
                risk_score += 2
                reasons.append(f"Many functions changed ({functions_count})")
            elif functions_count > 2:
                risk_score += 1
                reasons.append(f"Multiple functions changed ({functions_count})")
            
            if file_info['filename'].endswith(('.py', '.js', '.java', '.go')):
                # Core logic files
                risk_score += 1
            
            if risk_score >= 3:
                hotspots.append({
                    'filename': file_info['filename'],
                    'risk_score': risk_score,
                    'reasons': reasons,
                    'total_changes': total_changes,
                    'functions_changed': functions_count
                })
        
        return sorted(hotspots, key=lambda x: x['risk_score'], reverse=True)
    
    def extract_language_stats(self, files_changed: List[Dict]) -> Dict[str, int]:
        """Extract programming language statistics from changed files"""
        language_map = {
            'py': 'Python',
            'js': 'JavaScript',
            'ts': 'TypeScript',
            'java': 'Java',
            'go': 'Go',
            'rs': 'Rust',
            'cpp': 'C++',
            'c': 'C',
            'rb': 'Ruby',
            'php': 'PHP',
            'sh': 'Shell',
            'sql': 'SQL',
            'yml': 'YAML',
            'yaml': 'YAML',
            'json': 'JSON',
            'xml': 'XML',
            'html': 'HTML',
            'css': 'CSS',
            'md': 'Markdown'
        }
        
        stats = {}
        
        for file_info in files_changed:
            filename = file_info['filename']
            ext = filename.split('.')[-1] if '.' in filename else 'other'
            
            language = language_map.get(ext, ext)
            total_lines = file_info['additions'] + file_info['deletions']
            
            stats[language] = stats.get(language, 0) + total_lines
        
        return dict(sorted(stats.items(), key=lambda x: x[1], reverse=True))
    
    def extract_functions_from_patch(self, patch: str, filename: str) -> List[str]:
        """Extract function names from a patch"""
        ext = filename.split('.')[-1] if '.' in filename else ''
        pattern = self.function_patterns.get(ext)
        
        if not pattern:
            return []
        
        functions = []
        for line in patch.split('\n'):
            if line.startswith('+') or line.startswith('-'):
                match = re.search(pattern, line[1:])
                if match and match.group(1):
                    functions.append(match.group(1))
        
        return list(set(functions))  # Remove duplicates