# OnyxPoker API Documentation

## Overview
The OnyxPoker API provides poker-specific analysis using Kiro CLI for decision making.

## Base URL
```
http://54.80.204.92:5000
```

## Authentication
All requests (except /health) require Bearer token authentication:
```
Authorization: Bearer test_key_12345
```

## Endpoints

### Health Check
**GET** `/health`

Returns server health status. No authentication required.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-29T23:50:00.000Z"
}
```

### Analyze Poker State
**POST** `/analyze-poker`

Analyzes poker game state and returns AI decision.

**Request:**
```json
{
  "hero_cards": ["As", "Kh"],
  "community_cards": ["Qd", "Jc", "Ts"],
  "pot": 150,
  "hero_stack": 500,
  "to_call": 20,
  "position": "button",
  "num_opponents": 2
}
```

**Response:**
```json
{
  "action": "raise",
  "amount": 60,
  "reasoning": "Strong hand with straight draw, good pot odds",
  "confidence": 0.85
}
```

**Actions:**
- `fold` - Fold hand
- `call` - Call current bet
- `raise` - Raise (includes amount)

### Validate Game State
**POST** `/validate-state`

Validates detected game state using Kiro CLI vision analysis.

**Request:**
```json
{
  "screenshot": "base64_encoded_image",
  "detected_state": {
    "hero_cards": ["As", "Kh"],
    "pot": 150,
    "hero_stack": 500
  }
}
```

**Response:**
```json
{
  "valid": true,
  "confidence": 0.92,
  "concerns": []
}
```

## Error Responses

### Authentication Error
```json
{
  "error": "Unauthorized - Invalid API key"
}
```
Status: 401

### Bad Request
```json
{
  "error": "Missing required field: hero_cards"
}
```
Status: 400

### Server Error
```json
{
  "error": "Kiro CLI analysis failed"
}
```
Status: 500

## Rate Limiting
- Default: 60 requests per minute per API key
- Exceeded: HTTP 429 Too Many Requests

## Client Integration

### Python Example
```python
import requests

url = "http://54.80.204.92:5000/analyze-poker"
headers = {"Authorization": "Bearer test_key_12345"}
data = {
    "hero_cards": ["As", "Kh"],
    "community_cards": ["Qd", "Jc", "Ts"],
    "pot": 150,
    "hero_stack": 500,
    "to_call": 20
}

response = requests.post(url, json=data, headers=headers)
decision = response.json()
print(f"Action: {decision['action']}")
print(f"Reasoning: {decision['reasoning']}")
```

## Best Practices
1. Always include complete game state for accurate decisions
2. Handle errors gracefully with retry logic
3. Respect rate limits
4. Use HTTPS in production
5. Rotate API keys regularly
