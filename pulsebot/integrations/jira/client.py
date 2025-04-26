import logging
import requests
import base64
from datetime import datetime
from django.conf import settings
from core.models import IntegrationCredential

logger = logging.getLogger(__name__)

class JiraConnector:
    def __init__(self, user_id=None, team_id=None):
        self.user_id = user_id
        self.team_id = team_id
        self._load_credentials()
    
    def _load_credentials(self):
        """Load Jira credentials from the database."""
        if not self.user_id:
            self.token = None
            self.domain = None
            return
            
        try:
            cred = IntegrationCredential.objects.get(
                user_id=self.user_id,
                team_id=self.team_id,
                integration_type='jira'
            )
            
            self.token = cred.access_token
            # Domain should be stored in extra_data
            self.domain = cred.extra_data.get('domain')
            
            if not self.domain:
                logger.error("Jira domain not found in credentials")
        except IntegrationCredential.DoesNotExist:
            logger.warning(f"No Jira credentials for user {self.user_id}")
            self.token = None
            self.domain = None
    
    def _make_request(self, method, endpoint, data=None, params=None):
        """Make a request to the Jira API."""
        if not self.token or not self.domain:
            raise Exception("Jira credentials not available")
            
        url = f"https://{self.domain}.atlassian.net/rest/api/3{endpoint}"
        
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                json=data,
                params=params
            )
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.RequestException as e:
            logger.error(f"Jira API error: {e}")
            return None
    
    def get_projects(self):
        """Get all projects."""
        return self._make_request('GET', '/project')
    
    def get_project_issues(self, project_key, jql=None):
        """Get issues for a project."""
        params = {'jql': jql} if jql else {'jql': f'project = "{project_key}"'}
        return self._make_request('GET', '/search', params=params)
    
    def get_issue(self, issue_key):
        """Get details for a specific issue."""
        return self._make_request('GET', f'/issue/{issue_key}')
    
    def create_issue(self, project_key, issue_type, summary, description=None, fields=None):
        """Create a new issue."""
        data = {
            'fields': {
                'project': {'key': project_key},
                'summary': summary,
                'issuetype': {'name': issue_type}
            }
        }
        
        if description:
            data['fields']['description'] = {
                'type': 'doc',
                'version': 1,
                'content': [
                    {
                        'type': 'paragraph',
                        'content': [
                            {
                                'type': 'text',
                                'text': description
                            }
                        ]
                    }
                ]
            }
        
        if fields:
            data['fields'].update(fields)
            
        return self._make_request('POST', '/issue', data=data)
    
    def update_issue(self, issue_key, fields):
        """Update an existing issue."""
        data = {'fields': fields}
        return self._make_request('PUT', f'/issue/{issue_key}', data=data)