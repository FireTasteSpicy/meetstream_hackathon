import json
import logging
import hmac
import hashlib
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .services import GitHubService
from context_builder.trackers.services import ActivityTrackingService

logger = logging.getLogger(__name__)

@csrf_exempt
def github_webhook(request):
    """Handle incoming webhook events from GitHub."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # Parse the request body
    try:
        payload = json.loads(request.body)
        
        # Verify webhook signature if secret is configured
        if hasattr(settings, 'GITHUB_WEBHOOK_SECRET') and settings.GITHUB_WEBHOOK_SECRET:
            signature = request.headers.get('X-Hub-Signature-256')
            if not verify_signature(request.body, signature, settings.GITHUB_WEBHOOK_SECRET):
                return HttpResponse("Invalid signature", status=401)
        
        # Get the event type from headers
        event_type = request.headers.get('X-GitHub-Event')
        if not event_type:
            return JsonResponse({'error': 'No event type provided'}, status=400)
        
        # Add the event type to the payload for processing
        payload['event_type'] = event_type
        
        # Process the webhook event
        service = GitHubService()
        activity_tracker = ActivityTrackingService()
        
        # Process event
        if service.process_webhook_event(payload):
            # Track activity from the webhook event
            activity_tracker.track_github_event(payload)
            return JsonResponse({'success': True})
        else:
            logger.error(f"Failed to process GitHub webhook event: {event_type}")
            return JsonResponse({'error': 'Event processing failed'}, status=500)
            
    except json.JSONDecodeError:
        logger.error("Invalid JSON in GitHub webhook")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error processing GitHub webhook: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

def verify_signature(payload, signature, secret):
    """Verify the webhook signature from GitHub."""
    if not signature or not signature.startswith('sha256='):
        return False
        
    digest = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature[7:], digest)

@csrf_exempt
def github_auth(request):
    """Handle GitHub OAuth flow."""
    code = request.GET.get('code')
    if not code:
        return HttpResponse("Error: No code provided", status=400)
    
    service = GitHubService()
    result = service.complete_oauth(code, request.user)
    
    if result.get('success'):
        return HttpResponse("GitHub authentication successful! You can close this window.")
    else:
        return HttpResponse(f"Error during authentication: {result.get('error')}", status=400)