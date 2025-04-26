import logging
from django.utils import timezone
from django.contrib.auth.models import User
from .models import ActivityEvent, ActivityTracker
from .correlation import ActivityCorrelator

logger = logging.getLogger(__name__)

class ActivityTrackingService:
    def __init__(self):
        self.tracker = ActivityTracker()
        self.correlator = None  # Will be initialized when needed with user_id
    
    def track_github_event(self, payload, user_id=None):
        """Track an event from GitHub webhook."""
        try:
            # Extract GitHub event type from headers
            event_type = payload.get('event_type')  # This would be from headers in a real webhook
            
            if not user_id and payload.get('sender', {}).get('login'):
                # Try to find user by GitHub username
                try:
                    # This assumes GitHub username is stored in user.username
                    user = User.objects.get(username=payload['sender']['login'])
                    user_id = user.id
                except User.DoesNotExist:
                    logger.warning(f"No user found for GitHub username: {payload['sender']['login']}")
                    return False
            
            if not user_id:
                logger.error("No user ID provided for GitHub event")
                return False
            
            # Process based on event type
            if event_type == 'push':
                # Track commits
                for commit in payload.get('commits', []):
                    self.tracker.track_event(
                        user_id=user_id,
                        event_type='commit',
                        title=commit.get('message', '').split('\n')[0],
                        description=commit.get('message'),
                        metadata={
                            'commit_id': commit.get('id'),
                            'repository': payload.get('repository', {}).get('name')
                        },
                        source_system='github',
                        source_id=commit.get('id')
                    )
                return True
                
            elif event_type == 'pull_request':
                # Track PR events
                pr = payload.get('pull_request', {})
                action = payload.get('action')
                
                if action == 'opened':
                    event_subtype = 'pr_create'
                elif action == 'closed' and pr.get('merged'):
                    event_subtype = 'pr_merge'
                elif action in ['review_requested', 'review_request_removed']:
                    event_subtype = 'pr_review_request'
                elif action == 'submitted':
                    event_subtype = 'pr_review'
                else:
                    # Other PR actions we don't track specifically
                    return True
                
                self.tracker.track_event(
                    user_id=user_id,
                    event_type=event_subtype,
                    title=pr.get('title'),
                    description=pr.get('body'),
                    metadata={
                        'pr_number': pr.get('number'),
                        'repository': payload.get('repository', {}).get('name')
                    },
                    source_system='github',
                    source_id=str(pr.get('number'))
                )
                return True
                
            elif event_type == 'issues':
                # Track issue events
                issue = payload.get('issue', {})
                action = payload.get('action')
                
                if action == 'opened':
                    event_subtype = 'issue_create'
                elif action == 'closed':
                    event_subtype = 'issue_close'
                elif action == 'commented':
                    event_subtype = 'issue_comment'
                else:
                    # Other issue actions we don't track specifically
                    return True
                
                self.tracker.track_event(
                    user_id=user_id,
                    event_type=event_subtype,
                    title=issue.get('title'),
                    description=issue.get('body'),
                    metadata={
                        'issue_number': issue.get('number'),
                        'repository': payload.get('repository', {}).get('name')
                    },
                    source_system='github',
                    source_id=str(issue.get('number'))
                )
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error tracking GitHub event: {e}")
            return False
    
    def track_jira_event(self, payload, user_id=None):
        """Track an event from Jira webhook."""
        try:
            event_type = payload.get('webhookEvent')
            
            # Extract username from Jira event if user_id not provided
            if not user_id and payload.get('user', {}).get('name'):
                try:
                    # This assumes Jira username is stored somewhere in user profile
                    # In a real system, you'd need a mapping between Jira and local users
                    user = User.objects.filter(
                        username__icontains=payload['user']['name']
                    ).first()
                    
                    if user:
                        user_id = user.id
                except Exception as e:
                    logger.warning(f"Error finding user for Jira username: {e}")
            
            if not user_id:
                logger.error("No user ID provided for Jira event")
                return False
            
            # Process based on event type
            if 'issue_created' in event_type:
                issue = payload.get('issue', {})
                
                self.tracker.track_event(
                    user_id=user_id,
                    event_type='issue_create',
                    title=issue.get('fields', {}).get('summary', ''),
                    description=issue.get('fields', {}).get('description', ''),
                    metadata={
                        'issue_key': issue.get('key'),
                        'project': issue.get('fields', {}).get('project', {}).get('key')
                    },
                    source_system='jira',
                    source_id=issue.get('key', '')
                )
                return True
                
            elif 'issue_updated' in event_type:
                issue = payload.get('issue', {})
                changelog = payload.get('changelog', {})
                
                # Track status changes separately
                status_changes = [item for item in changelog.get('items', []) if item.get('field') == 'status']
                if status_changes:
                    for change in status_changes:
                        self.tracker.track_event(
                            user_id=user_id,
                            event_type='issue_update',
                            title=f"Status changed: {issue.get('key')}",
                            description=f"Status changed from {change.get('fromString')} to {change.get('toString')}",
                            metadata={
                                'issue_key': issue.get('key'),
                                'field_changed': 'status',
                                'from': change.get('fromString'),
                                'to': change.get('toString')
                            },
                            source_system='jira',
                            source_id=issue.get('key', '')
                        )
                
                # Track other significant updates
                self.tracker.track_event(
                    user_id=user_id,
                    event_type='issue_update',
                    title=f"Updated issue: {issue.get('key')}",
                    description=f"Updated fields: {', '.join([item.get('field') for item in changelog.get('items', [])])}",
                    metadata={
                        'issue_key': issue.get('key'),
                        'fields_changed': [item.get('field') for item in changelog.get('items', [])]
                    },
                    source_system='jira',
                    source_id=issue.get('key', '')
                )
                return True
                
            elif 'comment_created' in event_type:
                issue = payload.get('issue', {})
                comment = payload.get('comment', {})
                
                self.tracker.track_event(
                    user_id=user_id,
                    event_type='issue_comment',
                    title=f"Comment on {issue.get('key')}",
                    description=comment.get('body', '')[:200],
                    metadata={
                        'issue_key': issue.get('key'),
                        'comment_id': comment.get('id')
                    },
                    source_system='jira',
                    source_id=comment.get('id', '')
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error tracking Jira event: {e}")
            return False
    
    def track_slack_message(self, payload, user_id=None):
        """Track a message from Slack."""
        try:
            event = payload.get('event', {})
            
            if not event or event.get('type') != 'message' or event.get('bot_id'):
                # Skip non-message events or bot messages
                return False
            
            # Extract username from Slack event if user_id not provided
            if not user_id and event.get('user'):
                # In a real implementation, you'd have a mapping between Slack and local users
                # For now, we'll just log a warning
                logger.warning(f"No user mapping for Slack user ID: {event.get('user')}")
                return False
            
            if not user_id:
                logger.error("No user ID provided for Slack event")
                return False
            
            # Get message text
            text = event.get('text', '')
            channel = event.get('channel', '')
            
            # Track the message
            self.tracker.track_event(
                user_id=user_id,
                event_type='slack_message',
                title=f"Message in {channel}",
                description=text[:200],
                metadata={
                    'channel': channel,
                    'ts': event.get('ts'),
                    'thread_ts': event.get('thread_ts')
                },
                source_system='slack',
                source_id=event.get('ts', '')
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error tracking Slack message: {e}")
            return False
    
    def get_correlated_activities(self, user_id, days=7):
        """Get correlated activities for a user."""
        try:
            if not self.correlator or self.correlator.user_id != user_id:
                self.correlator = ActivityCorrelator(user_id=user_id)
            
            return self.correlator.correlate_activities(days=days)
            
        except Exception as e:
            logger.error(f"Error correlating activities: {e}")
            return {"error": str(e)}
    
    def get_user_workflow(self, user_id, days=30):
        """Get workflow patterns for a user."""
        try:
            if not self.correlator or self.correlator.user_id != user_id:
                self.correlator = ActivityCorrelator(user_id=user_id)
            
            return self.correlator.get_user_workflow_pattern(days=days)
            
        except Exception as e:
            logger.error(f"Error analyzing user workflow: {e}")
            return {"error": str(e)}