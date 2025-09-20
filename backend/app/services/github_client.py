"""
GitHub API client for fetching PR data and posting comments
"""

import jwt
import time
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.config import Settings
from app.logging import get_logger
from app.models.schemas import PRContext, PRFileModel, PRFileStatus
from app.services.diff_parser import DiffParser

logger = get_logger(__name__)


class GitHubClient:
    """GitHub API client with App authentication"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.app_id = settings.github_app_id
        self.private_key = settings.github_private_key
        self.base_url = "https://api.github.com"
        self._installation_tokens: Dict[int, Dict] = {}
    
    def _generate_jwt(self) -> str:
        """Generate JWT for GitHub App authentication"""
        if not self.private_key or not self.app_id:
            raise ValueError("GitHub App credentials not configured")
        
        payload = {
            'iat': int(time.time()) - 60,  # Issued 60 seconds in the past
            'exp': int(time.time()) + 600,  # Expires in 10 minutes
            'iss': self.app_id
        }
        
        return jwt.encode(payload, self.private_key, algorithm='RS256')
    
    def _get_installation_token(self, installation_id: int) -> str:
        """Get installation access token"""
        # Check if we have a valid cached token
        if installation_id in self._installation_tokens:
            token_data = self._installation_tokens[installation_id]
            expires_at = datetime.fromisoformat(token_data['expires_at'].replace('Z', '+00:00'))
            if expires_at > datetime.utcnow() + timedelta(minutes=5):
                return token_data['token']
        
        # Generate new token
        jwt_token = self._generate_jwt()
        
        response = requests.post(
            f"{self.base_url}/app/installations/{installation_id}/access_tokens",
            headers={
                'Authorization': f'Bearer {jwt_token}',
                'Accept': 'application/vnd.github+json'
            }
        )
        response.raise_for_status()
        
        token_data = response.json()
        self._installation_tokens[installation_id] = token_data
        
        return token_data['token']
    
    def _make_request(self, method: str, url: str, installation_id: int, **kwargs) -> requests.Response:
        """Make authenticated request to GitHub API"""
        token = self._get_installation_token(installation_id)
        
        headers = kwargs.get('headers', {})
        headers.update({
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github+json'
        })
        kwargs['headers'] = headers
        
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        
        return response
    
    def get_pr_details(self, repo_full_name: str, pr_number: int, installation_id: int) -> Dict[str, Any]:
        """Get PR details from GitHub API"""
        url = f"{self.base_url}/repos/{repo_full_name}/pulls/{pr_number}"
        response = self._make_request('GET', url, installation_id)
        return response.json()
    
    def get_pr_files(self, repo_full_name: str, pr_number: int, installation_id: int) -> List[Dict[str, Any]]:
        """Get list of files changed in PR"""
        url = f"{self.base_url}/repos/{repo_full_name}/pulls/{pr_number}/files"
        response = self._make_request('GET', url, installation_id)
        return response.json()
    
    def get_pr_diff(self, repo_full_name: str, pr_number: int, installation_id: int) -> str:
        """Get raw diff for PR"""
        url = f"{self.base_url}/repos/{repo_full_name}/pulls/{pr_number}"
        response = self._make_request(
            'GET', url, installation_id,
            headers={'Accept': 'application/vnd.github.v3.diff'}
        )
        return response.text
    
    def get_file_content(self, repo_full_name: str, file_path: str, ref: str, installation_id: int) -> str:
        """Get file content from repository"""
        url = f"{self.base_url}/repos/{repo_full_name}/contents/{file_path}"
        response = self._make_request(
            'GET', url, installation_id,
            params={'ref': ref}
        )
        
        file_data = response.json()
        if file_data.get('encoding') == 'base64':
            import base64
            return base64.b64decode(file_data['content']).decode('utf-8')
        
        return file_data.get('content', '')
    
    def post_pr_comment(self, repo_full_name: str, pr_number: int, body: str) -> Dict[str, Any]:
        """Post comment on PR"""
        # Extract installation_id from the current context
        # This is a simplified approach - in practice, you'd want to store this
        # during the webhook processing
        installation_id = getattr(self, '_current_installation_id', None)
        if not installation_id:
            raise ValueError("Installation ID not available")
        
        # First, check if we already have a comment from this bot
        existing_comment = self._find_existing_comment(repo_full_name, pr_number, installation_id)
        
        if existing_comment:
            # Update existing comment
            url = f"{self.base_url}/repos/{repo_full_name}/issues/comments/{existing_comment['id']}"
            response = self._make_request(
                'PATCH', url, installation_id,
                json={'body': body}
            )
        else:
            # Create new comment
            url = f"{self.base_url}/repos/{repo_full_name}/issues/{pr_number}/comments"
            response = self._make_request(
                'POST', url, installation_id,
                json={'body': body}
            )
        
        return response.json()
    
    def _find_existing_comment(self, repo_full_name: str, pr_number: int, installation_id: int) -> Optional[Dict[str, Any]]:
        """Find existing bot comment on PR"""
        url = f"{self.base_url}/repos/{repo_full_name}/issues/{pr_number}/comments"
        response = self._make_request('GET', url, installation_id)
        
        comments = response.json()
        bot_marker = "<!-- pr-auto-orchestrator: v1 -->"
        
        for comment in comments:
            if bot_marker in comment.get('body', ''):
                return comment
        
        return None
    
    def build_pr_context(self, pr_data: Dict[str, Any]) -> PRContext:
        """Build PR context from webhook data and GitHub API calls"""
        repo_full_name = pr_data['repo_full_name']
        pr_number = pr_data['pr_number']
        installation_id = pr_data['installation_id']
        
        # Store installation_id for later use
        self._current_installation_id = installation_id
        
        logger.info(
            "Building PR context",
            repo=repo_full_name,
            pr_number=pr_number
        )
        
        # Get PR details
        pr_details = self.get_pr_details(repo_full_name, pr_number, installation_id)
        
        # Get file changes
        files_data = self.get_pr_files(repo_full_name, pr_number, installation_id)
        
        # Get raw diff
        raw_diff = self.get_pr_diff(repo_full_name, pr_number, installation_id)
        
        # Parse files
        diff_parser = DiffParser()
        files = []
        language_stats = {}
        dependency_files = {}
        
        for file_data in files_data:
            filename = file_data['filename']
            
            # Map GitHub status to our enum
            status_map = {
                'added': PRFileStatus.ADDED,
                'modified': PRFileStatus.MODIFIED,
                'removed': PRFileStatus.REMOVED
            }
            
            file_model = PRFileModel(
                filename=filename,
                status=status_map.get(file_data['status'], PRFileStatus.MODIFIED),
                additions=file_data.get('additions', 0),
                deletions=file_data.get('deletions', 0),
                changes=file_data.get('changes', 0),
                patch=file_data.get('patch', '')
            )
            files.append(file_model)
            
            # Update language stats
            ext = filename.split('.')[-1] if '.' in filename else 'other'
            language_stats[ext] = language_stats.get(ext, 0) + file_model.additions + file_model.deletions
            
            # Check for dependency files
            if self._is_dependency_file(filename):
                try:
                    content = self.get_file_content(
                        repo_full_name, filename, pr_data['head_sha'], installation_id
                    )
                    dependency_files[filename] = content
                except Exception as e:
                    logger.warning(f"Could not fetch dependency file {filename}: {e}")
        
        return PRContext(
            run_id=pr_data['run_id'],
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            head_sha=pr_data['head_sha'],
            base_sha=pr_data['base_sha'],
            files=files,
            raw_diff=raw_diff,
            language_stats=language_stats,
            dependency_files=dependency_files,
            pr_title=pr_details.get('title', ''),
            pr_body=pr_details.get('body', ''),
            author=pr_details.get('user', {}).get('login', ''),
            labels=[label['name'] for label in pr_details.get('labels', [])]
        )
    
    def _is_dependency_file(self, filename: str) -> bool:
        """Check if file is a dependency file"""
        dependency_files = [
            'requirements.txt', 'requirements-dev.txt', 'Pipfile', 'pyproject.toml',
            'package.json', 'package-lock.json', 'yarn.lock',
            'Gemfile', 'Gemfile.lock',
            'pom.xml', 'build.gradle',
            'go.mod', 'go.sum'
        ]
        
        return any(filename.endswith(dep_file) for dep_file in dependency_files)