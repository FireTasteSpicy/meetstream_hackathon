import logging
import random
from enum import Enum
from orchestration.memory.personality import MemoryPersonalityController

logger = logging.getLogger(__name__)

class ActionType(Enum):
    DIRECT_RESPONSE = "direct_response"
    ASK_CLARIFICATION = "ask_clarification"
    SUGGEST_ACTION = "suggest_action"
    PROVIDE_RESOURCE = "provide_resource"
    NUDGE = "nudge"

class DecisionEngine:
    def __init__(self):
        self.mcp = MemoryPersonalityController()
        self.nudges = [
            "Have you considered writing tests for that code?",
            "Would you like me to help you document this feature?",
            "It might be worth reviewing this PR before merging.",
            "Consider sharing your progress with the team.",
            "Have you updated the project board with your latest progress?"
        ]
    
    def decide_action(self, prompt, user_id=None):
        """Decide what action to take based on the prompt and context."""
        # Get user context from MCP
        context = self.mcp.get_context(user_id, prompt) if user_id else {}
        
        # Simple decision logic based on prompt contents
        if "?" in prompt:
            # It's likely a question
            return ActionType.DIRECT_RESPONSE, None
        elif any(kw in prompt.lower() for kw in ['help', 'assist', 'support']):
            # User is asking for help
            return ActionType.DIRECT_RESPONSE, None
        elif any(kw in prompt.lower() for kw in ['unclear', 'confused', 'don\'t understand']):
            # User seems confused
            return ActionType.ASK_CLARIFICATION, "Could you provide more details about what you're trying to achieve?"
        elif any(kw in prompt.lower() for kw in ['resource', 'link', 'documentation', 'docs']):
            # User may be looking for resources
            return ActionType.PROVIDE_RESOURCE, None
        else:
            # Default to direct response with occasional nudges
            if random.random() < 0.2:  # 20% chance of nudge
                return ActionType.NUDGE, random.choice(self.nudges)
            return ActionType.DIRECT_RESPONSE, None
    
    def process_action(self, action_type, action_data, prompt, user_id=None):
        """Process the decided action."""
        if action_type == ActionType.DIRECT_RESPONSE:
            # Just return the prompt for direct processing
            return prompt
        
        elif action_type == ActionType.ASK_CLARIFICATION:
            # Return the clarification question instead of processing the original prompt
            return action_data or "Could you clarify what you mean?"
        
        elif action_type == ActionType.SUGGEST_ACTION:
            # Format a suggestion to the user
            return f"I suggest you: {action_data}" if action_data else prompt
        
        elif action_type == ActionType.PROVIDE_RESOURCE:
            # Format with a resource suggestion
            return f"{prompt}\n\nHere are some resources that might help:"
        
        elif action_type == ActionType.NUDGE:
            # Format with the nudge
            return f"{prompt}\n\nBy the way: {action_data}"
        
        # Default fallback
        return prompt