from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .generator import FollowUpGenerator

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_personal_followup(request):
    """API endpoint to get a personal follow-up summary."""
    days_back = int(request.query_params.get('days_back', 3))
    days_forward = int(request.query_params.get('days_forward', 3))
    
    generator = FollowUpGenerator()
    followup_content = generator.generate_individual_followup(
        request.user.id,
        days_back=days_back,
        days_forward=days_forward
    )
    
    return JsonResponse({
        'content': followup_content,
        'success': True
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_followup_email(request):
    """Send a follow-up summary via email."""
    generator = FollowUpGenerator()
    result = generator.send_followup_email(request.user.id)
    
    return JsonResponse(result)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_followup_slack(request):
    """Send a follow-up summary via Slack DM."""
    generator = FollowUpGenerator()
    result = generator.send_followup_slack(request.user.id)
    
    return JsonResponse(result)