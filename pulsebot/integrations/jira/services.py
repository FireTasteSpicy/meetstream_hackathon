import logging
import requests
import base64
from datetime import datetime
from django.contrib.auth.models import User
from django.conf import settings
from core.models import IntegrationCredential, Team

logger = logging.getLogger(__name__)

class JiraService:
    def __init__(self):
        self.base_url = "https://api.atlassian.com/oauth/token"
        self.api_url = "https://api.atlassian.com"
    
    def process_webhook_event(self, payload):
        """Process a webhook event from Jira."""
        event_type = payload.get('webhookEvent')
        
        try:
            if 'issue' in event_type:
                return self._handle_issue_event(payload)
            elif 'project' in event_type:
                return self._handle_project_event(payload)
            elif 'sprint' in event_type:
                return self._handle_sprint_event(payload)
            else:
                logger.info(f"Unhandled Jira event type: {event_type}")
                return True
        except Exception as e:
            logger.error(f"Error processing Jira event {event_type}: {e}")
            return False
    
    def _handle_issue_event(self, payload):
        """Handle an issue-related event from Jira."""
        event_type = payload.get('webhookEvent')
        issue = payload.get('issue', {})
        issue_key = issue.get('key')
        
        logger.info(f"Processing Jira issue event: {event_type} for {issue_key}")
        
        if 'created' in event_type:
            # New issue created
            pass
        elif 'updated' in event_type:
            # Issue updated
            changelog = payload.get('changelog', {})
            items = changelog.get('items', [])
            
            for item in items:
                field = item.get('field')
                if field == 'status':
                    # Status change
                    from_status = item.get('fromString')
                    to_status = item.get('toString')
                    logger.info(f"Status changed from {from_status} to {to_status}")
        
        return True
    
    def _handle_project_event(self, payload):
        """Handle a project-related event from Jira."""
        event_type = payload.get('webhookEvent')
        project = payload.get('project', {})
        
        logger.info(f"Processing Jira project event: {event_type}")
        return True
    
    def _handle_sprint_event(self, payload):
        """Handle a sprint-related event from Jira."""
        event_type = payload.get('webhookEvent')
        sprint = payload.get('sprint', {})
        
        logger.info(f"Processing Jira sprint event: {event_type}")
        return True
    
    def complete_oauth(self, code, user):
        """Complete the OAuth flow with Jira."""
        try:
            # Exchange code for access token
            response = requests.post(
                self.base_url,
                data={
                    'grant_type': 'authorization_code',
                    'client_id': settings.JIRA_CLIENT_ID,
                    'client_secret': settings.JIRA_CLIENT_SECRET,
                    'code': code,
                    'redirect_uri': settings.JIRA_REDIRECT_URI
                }
            )
            
            data = response.json()
            
            if 'error' in data:
                logger.error(f"Jira OAuth error: {data['error']}")
                return {'success': False, 'error': data.get('error_description', data['error'])}
            
            access_token = data.get('access_token')
            refresh_token = data.get('refresh_token')
            expires_in = data.get('expires_in')
            
            if not access_token:
                return {'success': False, 'error': 'No access token received'}
            
            # Get Jira cloud ID (needed for API calls)
            cloud_response = requests.get(
                f"{self.api_url}/oauth/token/accessible-resources",
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Accept': 'application/json'
                }
            )
            
            resources = cloud_response.json()
            if not resources or 'id' not in resources[0]:
                return {'success': False, 'error': 'Could not determine Jira cloud ID'}
                
            cloud_id = resources[0]['id']
            site_name = resources[0]['name']
            
            # Calculate expiration time
            expires_at = datetime.now() + datetime.timedelta(seconds=expires_in)
            
            # Store the tokens in the database
            IntegrationCredential.objects.update_or_create(
                user=user,
                integration_type='jira',
                defaults={
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'expires_at': expires_at,
                    'extra_data': {
                        'cloud_id': cloud_id,
                        'site_name': site_name,
                        'domain': site_name.lower().replace(' ', '-')
                    }
                }
            )
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Error completing Jira OAuth: {e}")
            return {'success': False, 'error': str(e)}