import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

class ActivityEvent(models.Model):
    EVENT_TYPES = (
        ('commit', 'Code Commit'),
        ('pr_create', 'PR Created'),
        ('pr_review', 'PR Reviewed'),
        ('pr_merge', 'PR Merged'),
        ('issue_create', 'Issue Created'),
        ('issue_comment', 'Issue Comment'),
        ('issue_close', 'Issue Closed'),
        ('standup', 'Standup Update'),
        ('meeting', 'Meeting'),
        ('blocker', 'Blocker Reported'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    source_system = models.CharField(max_length=50)  # github, jira, slack, etc.
    source_id = models.CharField(max_length=255, blank=True)  # ID in source system
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.user.username} - {self.event_type}: {self.title}"

class ActivityTracker:
    def __init__(self):
        pass
    
    def track_event(self, user_id, event_type, title, description="", metadata=None, source_system="pulsebot", source_id=""):
        """Track a new activity event."""
        try:
            user = User.objects.get(id=user_id)
            
            ActivityEvent.objects.create(
                user=user,
                event_type=event_type,
                title=title,
                description=description,
                metadata=metadata or {},
                source_system=source_system,
                source_id=source_id
            )
            
            return True
        except User.DoesNotExist:
            logger.error(f"Cannot track event: User {user_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error tracking activity event: {e}")
            return False
    
    def get_user_activity(self, user_id, days=7, event_types=None):
        """Get recent activity for a user."""
        try:
            start_date = timezone.now() - timedelta(days=days)
            
            query = ActivityEvent.objects.filter(
                user_id=user_id,
                created_at__gte=start_date
            )
            
            if event_types:
                query = query.filter(event_type__in=event_types)
                
            return query.order_by('-created_at')
        except Exception as e:
            logger.error(f"Error fetching user activity: {e}")
            return []
    
    def detect_blockers(self, user_id):
        """Detect potential blockers based on activity patterns."""
        blockers = []
        
        # Look for explicit blocker events
        explicit_blockers = ActivityEvent.objects.filter(
            user_id=user_id,
            event_type='blocker',
            created_at__gte=timezone.now() - timedelta(days=3)
        )
        
        for blocker in explicit_blockers:
            blockers.append({
                'type': 'reported',
                'title': blocker.title,
                'description': blocker.description,
                'created_at': blocker.created_at
            })
        
        # Look for PRs waiting for review for > 2 days
        stale_prs = ActivityEvent.objects.filter(
            user_id=user_id,
            event_type='pr_create',
            created_at__lte=timezone.now() - timedelta(days=2)
        )
        
        # In a real system, you'd check if these PRs have been reviewed/merged
        for pr in stale_prs:
            blockers.append({
                'type': 'stale_pr',
                'title': f"PR waiting: {pr.title}",
                'description': "This PR has been waiting for review for more than 2 days",
                'created_at': pr.created_at
            })
        
        return blockers