from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class PromptTemplate(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    template = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    prompt = models.TextField()
    response = models.TextField()
    source = models.CharField(max_length=50, default='web')
    context = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.user.username}: {self.prompt[:30]}..."