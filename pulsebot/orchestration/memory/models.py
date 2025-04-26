from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Memory(models.Model):
    """Long-term memory storage for user interactions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memories')
    key = models.CharField(max_length=255)
    value = models.JSONField()
    importance = models.FloatField(default=0.5)  # 0-1 scale of memory importance
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'key')
        verbose_name_plural = 'memories'
        
    def __str__(self):
        return f"{self.user.username}: {self.key}"

class UserPersonality(models.Model):
    """Stores personality traits and preferences for users"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='personality')
    traits = models.JSONField(default=dict)
    preferences = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Personality for {self.user.username}"

class ConversationContext(models.Model):
    """Stores context for ongoing conversations"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session_id = models.CharField(max_length=255)
    context = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Context for {self.user.username} - {self.session_id}"