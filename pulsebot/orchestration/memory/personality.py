import logging
import json
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth.models import User
from .models import Memory, UserPersonality, ConversationContext
from orchestration.prompt_manager.models import Conversation

logger = logging.getLogger(__name__)

class MemoryPersonalityController:
    def __init__(self):
        self.personality_traits = {
            'helpfulness': 0.9,  # 0-1 scale of how helpful the agent is
            'assertiveness': 0.6,  # 0-1 scale of how assertive the agent is
            'technical_depth': 0.8,  # 0-1 scale of how technical the agent gets
            'humor': 0.4,  # 0-1 scale of how humorous the agent is
        }
    
    def get_context(self, user_id, prompt):
        """Get contextual memory for a user and prompt."""
        context = {}
        
        if user_id:
            # Get recent conversations
            recent_convs = Conversation.objects.filter(
                user_id=user_id
            ).order_by('-created_at')[:5]
            
            if recent_convs:
                context['recent_conversations'] = [
                    {'prompt': c.prompt, 'response': c.response} 
                    for c in recent_convs
                ]
            
            # Get user memories
            memories = Memory.objects.filter(
                user_id=user_id
            ).order_by('-importance')[:10]
            
            if memories:
                context['memories'] = {m.key: m.value for m in memories}
            
            # Get user personality
            try:
                personality = UserPersonality.objects.get(user_id=user_id)
                context['user_preferences'] = personality.preferences
                context['user_traits'] = personality.traits
            except UserPersonality.DoesNotExist:
                pass
        
        # Add personality traits to context
        context['personality'] = self.personality_traits
        
        # Add current time for temporal context
        context['current_time'] = timezone.now().isoformat()
        
        return context
    
    def update_memory(self, user_id, prompt, response):
        """Update the agent's memory with a new interaction."""
        if not user_id:
            return
        
        try:
            user = User.objects.get(id=user_id)
            
            # Create or update user personality
            personality, created = UserPersonality.objects.get_or_create(user=user)
            
            # Extract key information from the interaction to store
            # This is a simple implementation - in production you'd use more 
            # sophisticated techniques to extract meaningful information
            
            # For demo purposes, we'll just store the last few topics
            words = prompt.lower().split()
            topics = [w for w in words if len(w) > 5][:3]  # Simple topic extraction
            
            for topic in topics:
                Memory.objects.update_or_create(
                    user=user,
                    key=f"topic_{topic}",
                    defaults={
                        'value': {
                            'last_mentioned': timezone.now().isoformat(),
                            'context': prompt[:100]
                        },
                        'importance': 0.7  # Arbitrary importance
                    }
                )
            
            logger.info(f"Updated memory for user {user_id}")
            return True
            
        except User.DoesNotExist:
            logger.error(f"Cannot update memory: User {user_id} not found")
            return False
    
    def adjust_personality(self, trait, value):
        """Adjust a personality trait."""
        if trait in self.personality_traits:
            self.personality_traits[trait] = max(0, min(1, value))
            return True
        return False
    
    def get_personality_profile(self):
        """Get the current personality profile."""
        return self.personality_traits