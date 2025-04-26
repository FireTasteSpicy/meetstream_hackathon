import logging
import requests
import json
from django.contrib.auth.models import User
from django.conf import settings
from core.models import IntegrationCredential, Team

logger = logging.getLogger(__name__)

class GitHubService:
    def __init__(self):
        self.api_url = "https://api.github.com"
        self.oauth_url = "https://github.com/login/oauth"
    
    def process_webhook_event(self, payload):
        """Process a webhook event from GitHub."""
        event_type = payload.get('event_type')
        
        try:
            if event_type == 'push':
                self._handle_push_event(payload)
            elif event_type == 'pull_request':
                self._handle_pr_event(payload)
            elif event_type == 'issues':
                self._handle_issue_event(payload)
            elif event_type == 'ping':
                # Just acknowledge ping events
                return True
            else:
                logger.info(f"Unhandled GitHub event type: {event_type}")
            
            return True
        except Exception as e:
            logger.error(f"Error processing GitHub event {event_type}: {e}")
            return False
    
    def _handle_push_event(self, payload):
        """Handle a push event from GitHub."""
        repository = payload.get('repository', {})
        repo_name = repository.get('name')
        logger.info(f"Push event received for repository: {repo_name}")
        
        # Process commits
        commits = payload.get('commits', [])
        logger.info(f"Processing {len(commits)} commits")
        
        # This is where you'd process commits, update databases, etc.
        return True
    
    def _handle_pr_event(self, payload):
        """Handle a pull request event from GitHub."""
        action = payload.get('action')
        pr = payload.get('pull_request', {})
        repo = payload.get('repository', {})
        
        logger.info(f"PR {action} - {pr.get('title')} in {repo.get('name')}")
        
        # Process based on PR action
        if action == 'opened':
            # New PR opened
            pass
        elif action == 'closed':
            # PR closed or merged
            if pr.get('merged'):
                # PR was merged
                pass
            else:
                # PR was closed without merge
                pass
        elif action == 'review_requested':
            # Someone was asked to review
            pass
        
        return True
    
    def _handle_issue_event(self, payload):
        """Handle an issue event from GitHub."""
        action = payload.get('action')
        issue = payload.get('issue', {})
        repo = payload.get('repository', {})
        
        logger.info(f"Issue {action} - {issue.get('title')} in {repo.get('name')}")
        
        # Process based on issue action
        if action == 'opened':
            # New issue opened
            pass
        elif action == 'closed':
            # Issue closed
            pass
        elif action == 'assigned':
            # Issue assigned to someone
            pass
        
        return True
    
    def complete_oauth(self, code, user):
        """Complete the OAuth flow with GitHub."""
        try:
            # Exchange code for access token
            response = requests.post(
                f"{self.oauth_url}/access_token",
                data={
                    'client_id': settings.GITHUB_CLIENT_ID,
                    'client_secret': settings.GITHUB_CLIENT_SECRET,
                    'code': code
                },
                headers={'Accept': 'application/json'}
            )
            
            data = response.json()
            
            if 'error' in data:
                logger.error(f"GitHub OAuth error: {data['error']}")
                return {'success': False, 'error': data['error']}
            
            access_token = data.get('access_token')
            
            if not access_token:
                return {'success': False, 'error': 'No access token received'}
            
            # Get user info from GitHub
            user_response = requests.get(
                f"{self.api_url}/user",
                headers={
                    'Authorization': f'token {access_token}',
                    'Accept': 'application/json'
                }
            )
            
            github_user = user_response.json()
            
            # Store the token in the database
            IntegrationCredential.objects.update_or_create(
                user=user,
                integration_type='github',
                defaults={
                    'access_token': access_token,
                    'extra_data': {
                        'github_username': github_user.get('login'),
                        'github_id': github_user.get('id'),
                        'avatar_url': github_user.get('avatar_url')
                    }
                }
            )
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Error completing GitHub OAuth: {e}")
            return {'success': False, 'error': str(e)}