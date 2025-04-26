import json
import logging
import hmac
import hashlib
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .services import JiraService
from context_builder.trackers.services import ActivityTrackingService

logger = logging.getLogger(__name__)

@csrf_exempt
def jira_webhook(request):
    """Handle incoming webhook events from Jira."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # Parse the request body
    try:
        payload = json.loads(request.body)
        
        # Verify webhook if secret is configured (Jira uses JWT for this in production)
        # This is simplified for the example
        if hasattr(settings, 'JIRA_WEBHOOK_SECRET') and settings.JIRA_WEBHOOK_SECRET:
            # In a real system, you'd verify using Jira's authentication method
            pass
        
        # Process the webhook event
        service = JiraService()
        activity_tracker = ActivityTrackingService()
        
        if service.process_webhook_event(payload):
            # Track activity from Jira
            # You'd need to adapt the activity tracker to handle Jira events
            # activity_tracker.track_jira_event(payload)
            return JsonResponse({'success': True})
        else:
            logger.error(f"Failed to process Jira webhook event")
            return JsonResponse({'error': 'Event processing failed'}, status=500)
            
    except json.JSONDecodeError:
        logger.error("Invalid JSON in Jira webhook")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error processing Jira webhook: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

@csrf_exempt
def jira_auth(request):
    """Handle Jira OAuth flow."""
    code = request.GET.get('code')
    if not code:
        return HttpResponse("Error: No code provided", status=400)
    
    service = JiraService()
    result = service.complete_oauth(code, request.user)
    
    if result.get('success'):
        return HttpResponse("Jira authentication successful! You can close this window.")
    else:
        return HttpResponse(f"Error during authentication: {result.get('error')}", status=400)