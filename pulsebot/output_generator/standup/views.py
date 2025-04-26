from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .generator import StandupGenerator

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def generate_standup(request):
    """API endpoint to generate a standup report."""
    generator = StandupGenerator()
    standup_content = generator.generate_standup(request.user.id)
    
    return JsonResponse({
        'content': standup_content,
        'success': True
    })