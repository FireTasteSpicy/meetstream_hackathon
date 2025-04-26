from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Team(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return self.name


class TeamMember(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('member', 'Member'),
        ('viewer', 'Viewer'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='members')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ('user', 'team')
        
    def __str__(self):
        return f"{self.user.username} - {self.team.name}"


class Project(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='projects')
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return self.name


class IntegrationCredential(models.Model):
    INTEGRATION_TYPES = (
        ('github', 'GitHub'),
        ('jira', 'Jira'),
        ('slack', 'Slack'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, null=True, blank=True)
    integration_type = models.CharField(max_length=20, choices=INTEGRATION_TYPES)
    access_token = models.CharField(max_length=1024)
    refresh_token = models.CharField(max_length=1024, blank=True, null=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    extra_data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        unique_together = ('user', 'team', 'integration_type')
    
    def __str__(self):
        team_name = self.team.name if self.team else "Personal"
        return f"{self.integration_type} - {self.user.username} - {team_name}"