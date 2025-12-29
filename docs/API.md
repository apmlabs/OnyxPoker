# OnyxPoker API Documentation

## Overview
The OnyxPoker API enables real-time screenshot analysis and GUI automation through HTTP endpoints.

## Authentication
All requests require Bearer token authentication:
```
Authorization: Bearer your_api_key_here
```

## Endpoints

### Health Check
**GET** `/health`

Returns server health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-29T12:19:00.000Z",
  "version": "1.0.0"
}
```

### Analyze Screenshot
**POST** `/analyze`

Analyzes a screenshot and returns recommended actions.

**Request:**
```json
{
  "image": "base64_encoded_png_data",
  "context": "Optional context or goal description"
}
```

**Response:**
```json
{
  "action": "click",
  "coordinates": [450, 300],
  "confidence": 0.85,
  "reasoning": "Detected login button at center of screen",
  "next_steps": ["Enter username", "Enter password", "Click login"],
  "goal_achieved": false
}
```

### Server Status
**GET** `/status`

Returns detailed server status and configuration.

**Response:**
```json
{
  "server": "OnyxPoker AI Analysis Server",
  "status": "running",
  "temp_dir": "/tmp/onyxpoker_screenshots",
  "kiro_cli_path": "kiro-cli",
  "timestamp": "2025-12-29T12:19:00.000Z"
}
```

## Action Types

### Click Action
```json
{
  "action": "click",
  "coordinates": [x, y],
  "confidence": 0.85
}
```

### Type Action
```json
{
  "action": "type",
  "text": "username@example.com",
  "confidence": 0.90
}
```

### Key Press Action
```json
{
  "action": "key",
  "key": "enter",
  "confidence": 0.95
}
```

### Wait Action
```json
{
  "action": "wait",
  "duration": 2.0,
  "confidence": 1.0
}
```

## Error Responses

### Authentication Error
```json
{
  "error": "Unauthorized"
}
```
Status: 401

### Bad Request
```json
{
  "error": "Missing image data"
}
```
Status: 400

### Server Error
```json
{
  "error": "Analysis failed: detailed error message"
}
```
Status: 500

## Rate Limiting
- Default: 60 requests per minute per API key
- Exceeded: HTTP 429 Too Many Requests

## Best Practices
1. Always include meaningful context in analysis requests
2. Handle errors gracefully with retry logic
3. Respect rate limits to avoid throttling
4. Use appropriate image compression to reduce payload size
5. Implement proper authentication token management
