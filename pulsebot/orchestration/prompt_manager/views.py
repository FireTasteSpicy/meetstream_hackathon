from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .services import PromptManager

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_prompt(request):
    """API endpoint to process a prompt."""
    prompt = request.data.get('prompt')
    context = request.data.get('context', {})
    
    if not prompt:
        return JsonResponse({'error': 'Prompt is required'}, status=400)
    
    # Process the prompt
    prompt_manager = PromptManager()
    response = prompt_manager.process_prompt(
        prompt=prompt, 
        user_id=request.user.id,
        source='api',
        **context
    )
    
    return JsonResponse({
        'response': response,
        'success': True
    })