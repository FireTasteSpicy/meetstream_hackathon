import logging
import requests
from datetime import datetime, timedelta
from django.conf import settings
from core.models import IntegrationCredential

logger = logging.getLogger(__name__)

class GitHubConnector:
    def __init__(self, user_id=None, team_id=None):
        self.base_url = 'https://api.github.com'
        self.user_id = user_id
        self.team_id = team_id
        self.token = self._get_token()
    
    def _get_token(self):
        """Get GitHub token from credentials store."""
        if not self.user_id:
            return None
            
        try:
            cred = IntegrationCredential.objects.get(
                user_id=self.user_id,
                team_id=self.team_id,
                integration_type='github'
            )
            
            # Check if token needs refresh
            if cred.expires_at and cred.expires_at <= datetime.now():
                # Implement token refresh logic here
                pass
                
            return cred.access_token
        except IntegrationCredential.DoesNotExist:
            logger.warning(f"No GitHub credentials for user {self.user_id}")
            return None
    
    def _make_request(self, method, endpoint, data=None, params=None):
        """Make a request to the GitHub API."""
        if not self.token:
            raise Exception("No GitHub token available")
            
        headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                json=data,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub API error: {e}")
            return None
    
    def get_user_repos(self, page=1, per_page=30):
        """Get repositories for the authenticated user."""
        return self._make_request(
            'GET', 
            '/user/repos',
            params={'page': page, 'per_page': per_page, 'sort': 'updated'}
        )
    
    def get_repo_details(self, owner, repo):
        """Get details for a specific repository."""
        return self._make_request('GET', f'/repos/{owner}/{repo}')
    
    def get_pull_requests(self, owner, repo, state='open'):
        """Get pull requests for a repository."""
        return self._make_request(
            'GET',
            f'/repos/{owner}/{repo}/pulls',
            params={'state': state}
        )
    
    def get_pr_details(self, owner, repo, pr_number):
        """Get details for a specific pull request."""
        return self._make_request('GET', f'/repos/{owner}/{repo}/pulls/{pr_number}')
    
    def create_issue(self, owner, repo, title, body=None, labels=None):
        """Create an issue in a repository."""
        data = {
            'title': title,
            'body': body,
        }
        
        if labels:
            data['labels'] = labels
            
        return self._make_request('POST', f'/repos/{owner}/{repo}/issues', data=data)