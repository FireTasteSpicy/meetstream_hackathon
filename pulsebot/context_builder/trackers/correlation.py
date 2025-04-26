import logging
import re
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q
from .models import ActivityEvent
from integrations.github.client import GitHubConnector
from integrations.jira.client import JiraConnector

logger = logging.getLogger(__name__)

class ActivityCorrelator:
    """Correlates activities between different systems (GitHub, Jira, Slack)"""
    
    def __init__(self, user_id=None, team_id=None):
        self.user_id = user_id
        self.team_id = team_id
        self.github = GitHubConnector(user_id=user_id, team_id=team_id)
        self.jira = JiraConnector(user_id=user_id, team_id=team_id)
    
    def correlate_activities(self, days=7):
        """Find correlations between activities across different systems."""
        if not self.user_id:
            return {"error": "User ID required for correlation"}
        
        start_date = timezone.now() - timedelta(days=days)
        
        # Get all activities for the user in the specified time period
        activities = ActivityEvent.objects.filter(
            user_id=self.user_id,
            created_at__gte=start_date
        ).order_by('created_at')
        
        # Group activities by source system
        github_activities = activities.filter(source_system='github')
        jira_activities = activities.filter(source_system='jira')
        slack_activities = activities.filter(source_system='slack')
        
        # Find correlations
        correlations = []
        
        # 1. Find commits related to Jira issues
        github_commits = github_activities.filter(event_type='commit')
        for commit in github_commits:
            # Look for Jira issue keys in commit messages (e.g., PROJECT-123)
            issue_keys = self._extract_jira_issues(commit.title) or self._extract_jira_issues(commit.description)
            
            for issue_key in issue_keys:
                # Find related Jira activities
                related_jira = jira_activities.filter(
                    Q(title__icontains=issue_key) | 
                    Q(description__icontains=issue_key) |
                    Q(source_id=issue_key)
                )
                
                if related_jira.exists():
                    correlations.append({
                        "type": "commit_to_issue",
                        "commit": {
                            "id": commit.id,
                            "title": commit.title,
                            "created_at": commit.created_at
                        },
                        "issues": [{
                            "id": issue.id,
                            "key": issue_key,
                            "title": issue.title,
                            "created_at": issue.created_at
                        } for issue in related_jira]
                    })
        
        # 2. Find PRs related to Jira issues
        github_prs = github_activities.filter(event_type__startswith='pr_')
        for pr in github_prs:
            # Look for Jira issue keys
            issue_keys = self._extract_jira_issues(pr.title) or self._extract_jira_issues(pr.description)
            
            for issue_key in issue_keys:
                # Find related Jira activities
                related_jira = jira_activities.filter(
                    Q(title__icontains=issue_key) | 
                    Q(description__icontains=issue_key) |
                    Q(source_id=issue_key)
                )
                
                if related_jira.exists():
                    correlations.append({
                        "type": "pr_to_issue",
                        "pr": {
                            "id": pr.id,
                            "title": pr.title,
                            "created_at": pr.created_at
                        },
                        "issues": [{
                            "id": issue.id,
                            "key": issue_key,
                            "title": issue.title,
                            "created_at": issue.created_at
                        } for issue in related_jira]
                    })
        
        # 3. Correlate Slack messages with GitHub and Jira activities
        for slack_msg in slack_activities:
            # Find referenced GitHub PRs in Slack messages
            if 'pull request' in slack_msg.description.lower() or 'pr' in slack_msg.description.lower():
                for pr in github_prs:
                    # Check if PR number or title is mentioned in Slack message
                    pr_metadata = pr.metadata or {}
                    pr_number = pr_metadata.get('pr_number')
                    
                    if pr_number and f"#{pr_number}" in slack_msg.description:
                        correlations.append({
                            "type": "slack_to_pr",
                            "slack_message": {
                                "id": slack_msg.id,
                                "text": slack_msg.description[:100],
                                "created_at": slack_msg.created_at
                            },
                            "pr": {
                                "id": pr.id,
                                "title": pr.title,
                                "number": pr_number,
                                "created_at": pr.created_at
                            }
                        })
            
            # Find referenced Jira issues in Slack messages
            issue_keys = self._extract_jira_issues(slack_msg.description)
            for issue_key in issue_keys:
                related_jira = jira_activities.filter(
                    Q(title__icontains=issue_key) | 
                    Q(description__icontains=issue_key) |
                    Q(source_id=issue_key)
                )
                
                if related_jira.exists():
                    correlations.append({
                        "type": "slack_to_issue",
                        "slack_message": {
                            "id": slack_msg.id,
                            "text": slack_msg.description[:100],
                            "created_at": slack_msg.created_at
                        },
                        "issues": [{
                            "id": issue.id,
                            "key": issue_key,
                            "title": issue.title,
                            "created_at": issue.created_at
                        } for issue in related_jira]
                    })
        
        # Get summary information
        summary = {
            "user_id": self.user_id,
            "period_days": days,
            "total_activities": activities.count(),
            "github_activities": github_activities.count(),
            "jira_activities": jira_activities.count(),
            "slack_activities": slack_activities.count(),
            "correlation_count": len(correlations)
        }
        
        return {
            "summary": summary,
            "correlations": correlations
        }
    
    def _extract_jira_issues(self, text):
        """Extract Jira issue keys from text (e.g., PROJECT-123)."""
        if not text:
            return []
        
        # Common Jira issue pattern
        pattern = r'([A-Z]+-\d+)'
        matches = re.findall(pattern, text)
        return matches
    
    def get_user_workflow_pattern(self, days=30):
        """Analyze user workflow patterns based on activity sequence."""
        if not self.user_id:
            return {"error": "User ID required for workflow analysis"}
        
        start_date = timezone.now() - timedelta(days=days)
        
        # Get all activities for the user in the specified time period
        activities = ActivityEvent.objects.filter(
            user_id=self.user_id,
            created_at__gte=start_date
        ).order_by('created_at')
        
        if not activities:
            return {
                "user_id": self.user_id,
                "message": "No activities found for this user in the specified time period",
                "patterns": []
            }
        
        # Track activity transitions (e.g., issue_create -> commit -> pr_create)
        transitions = []
        previous_activity = None
        
        for activity in activities:
            if previous_activity:
                time_diff = (activity.created_at - previous_activity.created_at).total_seconds() / 3600  # hours
                
                # Only track transitions that happen within 24 hours
                if time_diff <= 24:
                    transitions.append({
                        "from": previous_activity.event_type,
                        "to": activity.event_type,
                        "time_diff_hours": time_diff,
                        "from_system": previous_activity.source_system,
                        "to_system": activity.source_system
                    })
            
            previous_activity = activity
        
        # Analyze common patterns
        patterns = self._analyze_workflow_patterns(transitions, activities)
        
        return {
            "user_id": self.user_id,
            "activities_count": activities.count(),
            "activity_types": list(set([a.event_type for a in activities])),
            "transitions_count": len(transitions),
            "patterns": patterns
        }
    
    def _analyze_workflow_patterns(self, transitions, activities):
        """Analyze workflow transitions to identify patterns."""
        if not transitions:
            return []
        
        # Count frequency of each transition type
        transition_counts = {}
        for t in transitions:
            key = f"{t['from']}:{t['from_system']} -> {t['to']}:{t['to_system']}"
            if key not in transition_counts:
                transition_counts[key] = {
                    "count": 0,
                    "avg_time": 0,
                    "from_type": t['from'],
                    "to_type": t['to'],
                    "from_system": t['from_system'],
                    "to_system": t['to_system']
                }
            
            transition_counts[key]["count"] += 1
            # Running average calculation
            current_avg = transition_counts[key]["avg_time"]
            n = transition_counts[key]["count"]
            transition_counts[key]["avg_time"] = ((n-1) * current_avg + t["time_diff_hours"]) / n
        
        # Convert to list and sort by frequency
        patterns = list(transition_counts.values())
        patterns.sort(key=lambda x: x["count"], reverse=True)
        
        # Calculate most active hours
        hour_counts = {}
        for activity in activities:
            hour = activity.created_at.hour
            if hour not in hour_counts:
                hour_counts[hour] = 0
            hour_counts[hour] += 1
        
        # Find peak hours (top 3)
        peak_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Add additional insights
        insights = [
            {
                "type": "peak_hours",
                "description": f"Most active hours: {', '.join([f'{h}:00' for h, _ in peak_hours])}",
                "data": {
                    "peak_hours": [h for h, _ in peak_hours],
                    "counts": [c for _, c in peak_hours]
                }
            }
        ]
        
        # Find common sequences (3+ transitions)
        if len(activities) >= 3:
            common_sequences = self._find_common_sequences(activities)
            if common_sequences:
                insights.append({
                    "type": "common_sequences",
                    "description": "Common activity sequences detected",
                    "data": common_sequences[:3]  # Top 3 sequences
                })
        
        return {
            "transitions": patterns[:5],  # Top 5 most common transitions
            "insights": insights
        }
    
    def _find_common_sequences(self, activities):
        """Find common sequences of 3+ activities."""
        # Extract just the event types in temporal order
        activity_sequence = [a.event_type for a in activities]
        
        # Find all 3-event sequences
        sequences = {}
        for i in range(len(activity_sequence) - 2):
            seq = f"{activity_sequence[i]} -> {activity_sequence[i+1]} -> {activity_sequence[i+2]}"
            if seq not in sequences:
                sequences[seq] = 0
            sequences[seq] += 1
        
        # Sort by frequency
        sorted_sequences = sorted(sequences.items(), key=lambda x: x[1], reverse=True)
        
        return [{"sequence": s, "count": c} for s, c in sorted_sequences]