# Get personal followup
curl -X GET "http://localhost:8000/api/followup/?user_id=1&days_back=5&days_forward=3"

# Generate standup
curl -X GET "http://localhost:8000/api/standup/?user_id=1"

# Get team digest
curl -X GET "http://localhost:8000/api/digest/team/1/?days=2"

# Process prompt
curl -X POST http://localhost:8000/api/prompt/ \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What PRs are waiting for review?",
    "user_id": 1,
    "context": {"source": "api"}
  }'