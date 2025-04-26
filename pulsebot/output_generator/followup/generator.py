import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from context_builder.trackers.models import ActivityTracker, ActivityEvent
from context_builder.trackers.correlation import ActivityCorrelator

logger = logging.getLogger(__name__)

class FollowUpGenerator:
    """Generator for personalized follow-ups based on user activities and commitments"""
    
    def __init__(self):
        self.activity_tracker = ActivityTracker()
        
    def generate_individual_followup(self, user_id, days_back=3, days_forward=3):
        """Generate personalized follow-up summary for a user"""
        try:
            user = User.objects.get(id=user_id)
            
            # Calculate date ranges
            today = timezone.now().date()
            past_start = today - timedelta(days=days_back)
            future_end = today + timedelta(days=days_forward)
            
            # Get user activity from the past days
            past_activities = ActivityEvent.objects.filter(
                user=user,
                created_at__gte=datetime.combine(past_start, datetime.min.time()),
                created_at__lte=datetime.combine(today, datetime.max.time())
            ).order_by('-created_at')
            
            # Get potential blockers
            blockers = self.activity_tracker.detect_blockers(user_id)
            
            # Find pending commitments (extracted from PR comments, issues, etc.)
            pending_commitments = self._extract_commitments(user_id)
            
            # Get correlations between activities to provide context
            correlator = ActivityCorrelator(user_id=user_id)
            correlations = correlator.correlate_activities(days=days_back)
            
            # Generate the follow-up content
            followup = {
                'user': user.username,
                'date': today.strftime('%Y-%m-%d'),
                'recent_activities': self._summarize_activities(past_activities),
                'blockers': blockers,
                'pending_commitments': pending_commitments,
                'activity_correlations': correlations.get('correlations', [])[:5] if isinstance(correlations, dict) else [],
                'suggestions': self._generate_suggestions(past_activities, blockers, pending_commitments)
            }
            
            # Format the follow-up summary
            return self._format_followup(followup)
            
        except User.DoesNotExist:
            logger.error(f"User {user_id} not found")
            return "Error: User not found"
        except Exception as e:
            logger.error(f"Error generating individual follow-up: {e}")
            return f"Error generating follow-up: {str(e)}"
    
    def _summarize_activities(self, activities):
        """Summarize a list of activities into categories"""
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
        
        # Summarize PRs by status
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
        
        # Summarize issues by status
        if issues:
            issue_created = [i for i in issues if i.event_type == 'issue_create']
            issue_closed = [i for i in issues if i.event_type == 'issue_close']
            issue_comments = [i for i in issues if i.event_type == 'issue_comment']
            
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
                
            if issue_comments:
                summary.append({
                    'type': 'issue_comments',
                    'count': len(issue_comments),
                    'details': [i.title for i in issue_comments][:5]
                })
            
        return summary
    
    def _extract_commitments(self, user_id):
        """Extract commitments the user has made in comments and messages"""
        today = timezone.now().date()
        month_ago = today - timedelta(days=30)
        
        # Look for activities containing commitment-like phrases
        commitment_phrases = ['i will', 'i\'ll', 'i can', 'i should', 'todo', 'to do', 'need to', 'going to']
        
        # Search in comments, messages, PR descriptions, etc.
        potential_commitments = []
        
        # Search issue comments
        issue_comments = ActivityEvent.objects.filter(
            user_id=user_id,
            event_type='issue_comment',
            created_at__gte=datetime.combine(month_ago, datetime.min.time()),
        )
        
        for comment in issue_comments:
            desc_lower = comment.description.lower()
            if any(phrase in desc_lower for phrase in commitment_phrases):
                potential_commitments.append({
                    'source': 'issue_comment',
                    'source_id': comment.source_id,
                    'text': comment.description,
                    'date': comment.created_at,
                    'context': comment.title,
                    'status': 'pending'  # Default status
                })
        
        # Search PR descriptions
        pr_activities = ActivityEvent.objects.filter(
            user_id=user_id,
            event_type='pr_create',
            created_at__gte=datetime.combine(month_ago, datetime.min.time()),
        )
        
        for pr in pr_activities:
            desc_lower = pr.description.lower() if pr.description else ""
            if any(phrase in desc_lower for phrase in commitment_phrases):
                potential_commitments.append({
                    'source': 'pull_request',
                    'source_id': pr.source_id,
                    'text': pr.description,
                    'date': pr.created_at,
                    'context': pr.title,
                    'status': 'pending'  # Default status
                })
        
        return potential_commitments
    
    def _generate_suggestions(self, activities, blockers, commitments):
        """Generate personalized suggestions based on activities and blockers"""
        suggestions = []
        
        # Suggest addressing blockers
        if blockers:
            for blocker in blockers:
                suggestions.append({
                    'type': 'blocker',
                    'message': f"Address blocker: {blocker['title']}"
                })
        
        # Suggest following up on pending commitments
        for commitment in commitments:
            # Only suggest if commitment is more than 3 days old
            if (timezone.now() - commitment['date']).days > 3:
                suggestions.append({
                    'type': 'commitment',
                    'message': f"Follow up on: {commitment['context']}",
                    'context': commitment['text'][:100]
                })
        
        # Suggest PR reviews if there are created PRs but no reviews
        pr_created = [a for a in activities if a.event_type == 'pr_create']
        pr_reviewed = [a for a in activities if a.event_type == 'pr_review']
        
        if pr_created and not pr_reviewed:
            suggestions.append({
                'type': 'workflow',
                'message': "Follow up on your open PRs that need review"
            })
            
        return suggestions
    
    def _format_followup(self, followup):
        """Format a follow-up summary in markdown"""
        md = f"# Personal Follow-Up for {followup['user']} - {followup['date']}\n\n"
        
        # Highlight blockers first if there are any
        if followup['blockers']:
            md += "## 🚨 Blockers Requiring Attention\n\n"
            for blocker in followup['blockers']:
                md += f"- **{blocker['title']}**: {blocker['description']}\n"
            md += "\n"
        
        # Recent Activities
        md += "## Recent Activities\n\n"
        if followup['recent_activities']:
            for activity in followup['recent_activities']:
                md += f"### {activity['type'].replace('_', ' ').title()} ({activity['count']})\n\n"
                for detail in activity['details']:
                    md += f"- {detail}\n"
                md += "\n"
        else:
            md += "No activities recorded recently.\n\n"
        
        # Pending Commitments
        if followup['pending_commitments']:
            md += "## Pending Commitments\n\n"
            for commitment in followup['pending_commitments']:
                date_str = commitment['date'].strftime('%Y-%m-%d')
                md += f"- **{date_str}**: {commitment['context']}\n"
                md += f"  - *\"{commitment['text'][:150]}{'...' if len(commitment['text']) > 150 else ''}\"*\n"
            md += "\n"
        
        # Related Work
        if followup['activity_correlations']:
            md += "## Related Work\n\n"
            for correlation in followup['activity_correlations']:
                if correlation['type'] == 'pr_to_issue':
                    md += f"- PR **{correlation['pr']['title']}** is related to issue **{correlation['issues'][0]['title']}**\n"
                elif correlation['type'] == 'commit_to_issue':
                    md += f"- Commit **{correlation['commit']['title']}** addresses issue **{correlation['issues'][0]['title']}**\n"
            md += "\n"
        
        # Suggestions
        if followup['suggestions']:
            md += "## Suggested Actions\n\n"
            for suggestion in followup['suggestions']:
                md += f"- {suggestion['message']}\n"
                if 'context' in suggestion:
                    md += f"  - Context: *{suggestion['context']}*\n"
            md += "\n"
        
        return md
    
    def send_followup_email(self, user_id):
        """Generate and send a follow-up email to a user"""
        try:
            user = User.objects.get(id=user_id)
            
            # Generate the follow-up
            followup_content = self.generate_individual_followup(user_id)
            
            # In a real implementation, you'd send an email here
            # For this example, we'll just log it
            logger.info(f"Would send email to {user.email} with follow-up")
            
            return {
                'success': True,
                'recipient': user.email,
                'content': followup_content
            }
            
        except Exception as e:
            logger.error(f"Error sending follow-up email: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_followup_notification(self, user_id, notification_type='email'):
        """Generate and send a follow-up notification of the specified type"""
        try:
            user = User.objects.get(id=user_id)
            
            # Generate the follow-up content
            followup_content = self.generate_individual_followup(user_id)
            
            # Return the raw content that can be sent by any frontend
            return {
                'success': True,
                'recipient': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                },
                'notification_type': notification_type,
                'content': followup_content,
                'timestamp': timezone.now().isoformat()
            }
                
        except Exception as e:
            logger.error(f"Error preparing follow-up notification: {e}")
            return {
                'success': False,
                'error': str(e)
            }