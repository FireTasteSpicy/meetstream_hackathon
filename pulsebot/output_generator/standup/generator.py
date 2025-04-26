import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from context_builder.trackers.models import ActivityTracker, ActivityEvent

logger = logging.getLogger(__name__)

class StandupGenerator:
    def __init__(self):
        self.activity_tracker = ActivityTracker()
    
    def generate_standup(self, user_id):
        """Generate a standup summary for a user."""
        try:
            user = User.objects.get(id=user_id)
            
            # Get yesterday's date
            yesterday = timezone.now().date() - timedelta(days=1)
            yesterday_start = datetime.combine(yesterday, datetime.min.time())
            yesterday_end = datetime.combine(yesterday, datetime.max.time())
            
            # Get today's date
            today = timezone.now().date()
            today_start = datetime.combine(today, datetime.min.time())
            
            # Get yesterday's activities
            yesterday_activities = ActivityEvent.objects.filter(
                user=user,
                created_at__gte=yesterday_start,
                created_at__lte=yesterday_end
            ).order_by('created_at')
            
            # Get today's activities (so far)
            today_activities = ActivityEvent.objects.filter(
                user=user,
                created_at__gte=today_start
            ).order_by('created_at')
            
            # Detect blockers
            blockers = self.activity_tracker.detect_blockers(user_id)
            
            # Generate summary
            standup = {
                'user': user.username,
                'date': today.strftime('%Y-%m-%d'),
                'yesterday': self._summarize_activities(yesterday_activities),
                'today': self._summarize_activities(today_activities),
                'blockers': blockers
            }
            
            # Format the standup summary
            return self._format_standup(standup)
        except User.DoesNotExist:
            logger.error(f"User {user_id} not found")
            return "Error: User not found"
        except Exception as e:
            logger.error(f"Error generating standup: {e}")
            return f"Error generating standup: {str(e)}"
    
    def _summarize_activities(self, activities):
        """Summarize a list of activities."""
        summary = []
        
        # Group by event type
        commits = [a for a in activities if a.event_type == 'commit']
        prs = [a for a in activities if a.event_type.startswith('pr_')]
        issues = [a for a in activities if a.event_type.startswith('issue_')]
        
        # Summarize commits
        if commits:
            summary.append({
                'type': 'commits',
                'count': len(commits),
                'details': [c.title for c in commits[:5]]
            })
        
        # Summarize PRs
        if prs:
            pr_created = [p for p in prs if p.event_type == 'pr_create']
            pr_reviewed = [p for p in prs if p.event_type == 'pr_review']
            pr_merged = [p for p in prs if p.event_type == 'pr_merge']
            
            if pr_created:
                summary.append({
                    'type': 'pr_created',
                    'count': len(pr_created),
                    'details': [p.title for p in pr_created]
                })
            
            if pr_reviewed:
                summary.append({
                    'type': 'pr_reviewed',
                    'count': len(pr_reviewed),
                    'details': [p.title for p in pr_reviewed]
                })
                
            if pr_merged:
                summary.append({
                    'type': 'pr_merged',
                    'count': len(pr_merged),
                    'details': [p.title for p in pr_merged]
                })
        
        # Summarize issues
        if issues:
            issue_created = [i for i in issues if i.event_type == 'issue_create']
            issue_closed = [i for i in issues if i.event_type == 'issue_close']
            
            if issue_created:
                summary.append({
                    'type': 'issues_created',
                    'count': len(issue_created),
                    'details': [i.title for i in issue_created]
                })
                
            if issue_closed:
                summary.append({
                    'type': 'issues_closed',
                    'count': len(issue_closed),
                    'details': [i.title for i in issue_closed]
                })
        
        # Add other activity types as needed
        other = [a for a in activities if a.event_type not in ['commit', 'pr_create', 'pr_review', 'pr_merge', 'issue_create', 'issue_close']]
        if other:
            summary.append({
                'type': 'other',
                'count': len(other),
                'details': [f"{a.event_type}: {a.title}" for a in other]
            })
            
        return summary
    
    def _format_standup(self, standup):
        """Format a standup summary in markdown."""
        md = f"# Daily Standup for {standup['user']} - {standup['date']}\n\n"
        
        # Yesterday section
        md += "## Yesterday\n\n"
        if standup['yesterday']:
            for item in standup['yesterday']:
                md += f"### {item['type'].replace('_', ' ').title()} ({item['count']})\n\n"
                for detail in item['details']:
                    md += f"- {detail}\n"
                md += "\n"
        else:
            md += "No activity recorded.\n\n"
        
        # Today section
        md += "## Today\n\n"
        if standup['today']:
            for item in standup['today']:
                md += f"### {item['type'].replace('_', ' ').title()} ({item['count']})\n\n"
                for detail in item['details']:
                    md += f"- {detail}\n"
                md += "\n"
        else:
            md += "No activity recorded yet.\n\n"
        
        # Blockers section
        md += "## Blockers\n\n"
        if standup['blockers']:
            for blocker in standup['blockers']:
                md += f"- **{blocker['title']}**: {blocker['description']}\n"
        else:
            md += "No blockers reported.\n"
        
        return md