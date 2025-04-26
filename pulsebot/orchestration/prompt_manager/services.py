import logging
import os
import google.generativeai as genai
from django.conf import settings
from django.contrib.auth.models import User
from .models import Conversation, PromptTemplate
from orchestration.memory.personality import MemoryPersonalityController
from orchestration.decision_engine.engine import DecisionEngine, ActionType

logger = logging.getLogger(__name__)

class PromptManager:
    def __init__(self):
        self.mcp = MemoryPersonalityController()
        self.decision_engine = DecisionEngine()
        
        # Initialize Gemini API with Google API key
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
    
    def process_prompt(self, prompt, user_id=None, source='web', **kwargs):
        """Process a prompt and return a response."""
        # Get the user if user_id is provided
        user = None
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                logger.warning(f"User with ID {user_id} not found")
        
        # Get context from MCP
        context = self.mcp.get_context(user_id, prompt)
        
        # Let the decision engine decide what action to take
        action_type, action_data = self.decision_engine.decide_action(prompt, user_id)
        
        # Process the action
        processed_prompt = self.decision_engine.process_action(action_type, action_data, prompt, user_id)
        
        # Prepare the complete prompt with context
        full_prompt = self._prepare_prompt(processed_prompt, context)
        
        # Get response from LLM
        response = self._call_llm(full_prompt)
        
        # Save the conversation
        if user:
            Conversation.objects.create(
                user=user,
                prompt=prompt,
                response=response,
                source=source,
                context=kwargs
            )
        
        # Update memory with the new conversation
        self.mcp.update_memory(user_id, prompt, response)
        
        return response
    
    def _prepare_prompt(self, prompt, context):
        """Prepare the complete prompt with context."""
        # Here you'd typically format the prompt with the context
        if context:
            context_str = "\n\nContext:\n" + "\n".join([f"- {k}: {v}" for k, v in context.items() if k != 'memories'])
            
            # Add memories in a more structured way if available
            if 'memories' in context:
                context_str += "\n\nPrevious knowledge:\n"
                for key, value in context['memories'].items():
                    context_str += f"- {key}: {value}\n"
                
            return f"{prompt}{context_str}"
        return prompt
    
    def _call_llm(self, prompt):
        """Call the Gemini LLM and return the response."""
        try:
            # Create system instruction
            system_instruction = "You are PulseBot, a helpful assistant for software development teams."
            
            # Generate content using Gemini
            response = self.model.generate_content(
                [system_instruction, prompt],
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=1000,
                )
            )
            
            # Extract the text from the response
            return response.text
            
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            return "I'm sorry, I encountered an error processing your request."