from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .generator import DigestGenerator
from core.models import Team, TeamMember

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def generate_team_digest(request, team_id):
    """API endpoint to generate a team digest."""
    days = int(request.query_params.get('days', 1))
    
    # Check if user has access to this team
    try:
        TeamMember.objects.get(user=request.user, team_id=team_id)
    except TeamMember.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'You do not have access to this team'
        }, status=403)
    
    generator = DigestGenerator()
    digest_content = generator.generate_team_digest(team_id, days)
    
    return JsonResponse({
        'content': digest_content,
        'success': True
    })