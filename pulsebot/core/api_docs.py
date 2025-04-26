from django.http import JsonResponse

def api_docs(request):
    """Return API documentation"""
    api_endpoints = {
        "auth": {
            "/api/token/": "POST - Obtain authentication token",
        },
        "prompt_manager": {
            "/api/prompt/": "POST - Process a natural language prompt",
        },
        "output_generators": {
            "/api/standup/": "GET - Generate a standup report",
            "/api/followup/": "GET - Get personal followup",
            "/api/followup/send-email/": "POST - Send followup via email",
            "/api/digest/team/{team_id}/": "GET - Generate team digest",
        },
        "integrations": {
            "/api/github/webhook/": "POST - GitHub webhook endpoint",
            "/api/github/auth/": "GET - GitHub OAuth callback",
            "/api/jira/webhook/": "POST - Jira webhook endpoint",
            "/api/jira/auth/": "GET - Jira OAuth callback",
        }
    }
    
    return JsonResponse({
        "name": "PulseBot API",
        "version": "1.0.0",
        "description": "Backend API for PulseBot - Developer productivity assistant",
        "endpoints": api_endpoints
    })