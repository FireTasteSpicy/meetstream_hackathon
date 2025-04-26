import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from context_builder.trackers.models import ActivityTracker, ActivityEvent

logger = logging.getLogger(__name__)

class DigestGenerator:
    def __init__(self):
        self.activity_tracker = ActivityTracker()
    
    def generate_team_digest(self, team_id, days=1):
        """Generate a team digest for the specified number of days."""
        from core.models import Team, TeamMember
        
        try:
            team = Team.objects.get(id=team_id)
            members = TeamMember.objects.filter(team=team)
            
            # Get the date range
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            
            digest = {
                'team': team.name,
                'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                'total_activities': 0,
                'member_summaries': [],
                'top_projects': [],
                'recent_prs': [],
                'recent_issues': [],
                'blockers': []
            }
            
            # Process each team member
            for member in members:
                user_activities = ActivityEvent.objects.filter(
                    user=member.user,
                    created_at__gte=start_date,
                    created_at__lte=end_date
                )
                
                user_summary = {
                    'name': member.user.get_full_name() or member.user.username,
                    'activity_count': user_activities.count(),
                    'pr_count': user_activities.filter(event_type__startswith='pr_').count(),
                    'commit_count': user_activities.filter(event_type='commit').count(),
                    'issue_count': user_activities.filter(event_type__startswith='issue_').count(),
                    'blockers': self.activity_tracker.detect_blockers(member.user.id)
                }
                
                digest['member_summaries'].append(user_summary)
                digest['total_activities'] += user_summary['activity_count']
                
                # Add blockers to team blockers list
                for blocker in user_summary['blockers']:
                    digest['blockers'].append({
                        'user': user_summary['name'],
                        'title': blocker['title'],
                        'description': blocker['description']
                    })
            
            # Get all PRs from the time period, across all team members
            all_prs = ActivityEvent.objects.filter(
                user__in=[m.user for m in members],
                event_type__startswith='pr_',
                created_at__gte=start_date,
                created_at__lte=end_date
            ).order_by('-created_at')
            
            # Add recent PRs to the digest
            digest['recent_prs'] = [{
                'title': pr.title,
                'user': pr.user.username,
                'type': pr.event_type,
                'date': pr.created_at
            } for pr in all_prs[:10]]
            
            # Get all issues from the time period
            all_issues = ActivityEvent.objects.filter(
                user__in=[m.user for m in members],
                event_type__startswith='issue_',
                created_at__gte=start_date,
                created_at__lte=end_date
            ).order_by('-created_at')
            
            # Add recent issues to the digest
            digest['recent_issues'] = [{
                'title': issue.title,
                'user': issue.user.username,
                'type': issue.event_type,
                'date': issue.created_at
            } for issue in all_issues[:10]]
            
            return self._format_team_digest(digest)
            
        except Team.DoesNotExist:
            logger.error(f"Team {team_id} not found")
            return "Error: Team not found"
        except Exception as e:
            logger.error(f"Error generating team digest: {e}")
            return f"Error generating team digest: {str(e)}"
    
    def _format_team_digest(self, digest):
        """Format a team digest in Markdown."""
        md = f"# Team Digest: {digest['team']}\n\n"
        md += f"**Period**: {digest['period']}\n"
        md += f"**Total Activities**: {digest['total_activities']}\n\n"
        
        # Team Member Summaries
        md += "## Team Member Summaries\n\n"
        for member in digest['member_summaries']:
            md += f"### {member['name']}\n"
            md += f"- **Activities**: {member['activity_count']}\n"
            md += f"- **PRs**: {member['pr_count']}\n"
            md += f"- **Commits**: {member['commit_count']}\n"
            md += f"- **Issues**: {member['issue_count']}\n"
            
            if member['blockers']:
                md += f"- **Blockers**: {len(member['blockers'])}\n"
            
            md += "\n"
        
        # Recent PRs
        if digest['recent_prs']:
            md += "## Recent Pull Requests\n\n"
            for pr in digest['recent_prs']:
                md += f"- **{pr['title']}** by {pr['user']} ({pr['type'].replace('_', ' ')}) - {pr['date'].strftime('%Y-%m-%d')}\n"
            md += "\n"
        
        # Recent Issues
        if digest['recent_issues']:
            md += "## Recent Issues\n\n"
            for issue in digest['recent_issues']:
                md += f"- **{issue['title']}** by {issue['user']} ({issue['type'].replace('_', ' ')}) - {issue['date'].strftime('%Y-%m-%d')}\n"
            md += "\n"
        
        # Blockers
        if digest['blockers']:
            md += "## Team Blockers\n\n"
            for blocker in digest['blockers']:
                md += f"- **{blocker['user']}**: {blocker['title']} - {blocker['description']}\n"
        
        return md
    
    def send_digest(self, team_id, days=1):
        """Generate a digest and return it as data."""
        try:
            digest_content = self.generate_team_digest(team_id, days)
            
            return {
                'success': True,
                'content': digest_content
            }
        except Exception as e:
            logger.error(f"Error sending digest: {e}")
            return {
                'success': False,
                'error': str(e)
            }