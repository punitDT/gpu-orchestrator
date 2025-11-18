# API Documentation

Complete API reference for the GPU Orchestrator service.

## Base URL

- **Local**: `http://localhost:8080`
- **Production**: `https://your-app.fly.dev`

## Authentication

Currently no authentication required. **Add authentication before production deployment.**

## Standard Response Format

All endpoints return responses in this format:

```json
{
  "status": "success|error|warming_up",
  "message": "Human-readable message",
  "data": { /* endpoint-specific data */ },
  "request_id": "uuid-v4-string"
}
```

## Endpoints

### 1. Health Check

Check if the service is running.

**Endpoint**: `GET /health`

**Response**: `200 OK`

```json
{
  "status": "healthy",
  "message": "Service is running",
  "data": {
    "timestamp": "2024-01-15T10:30:00Z",
    "version": "1.0.0"
  }
}
```

**Example**:
```bash
curl http://localhost:8080/health
```

---

### 2. GPU Status

Get current GPU instance status and idle time.

**Endpoint**: `GET /gpu-status`

**Response**: `200 OK`

```json
{
  "status": "success",
  "message": "GPU status retrieved",
  "data": {
    "gpu_running": true,
    "idle_time_seconds": 45.2,
    "last_request_time": "2024-01-15T10:29:15Z"
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Fields**:
- `gpu_running`: Boolean indicating if GPU is currently running
- `idle_time_seconds`: Time since last request (null if no requests yet)
- `last_request_time`: ISO 8601 timestamp of last request (null if no requests yet)

**Example**:
```bash
curl http://localhost:8080/gpu-status
```

---

### 3. Generate Logo

Generate a logo using the GPU worker.

**Endpoint**: `POST /generate-logo`

**Request Body**:

```json
{
  "prompt": "A modern minimalist logo for a tech startup",
  "width": 512,
  "height": 512,
  "num_inference_steps": 20
}
```

**Request Fields**:
- `prompt` (required): Text description of the logo (1-1000 characters)
- `width` (optional): Image width in pixels (256-2048, default: 512)
- `height` (optional): Image height in pixels (256-2048, default: 512)
- `num_inference_steps` (optional): Number of inference steps (1-100, default: 20)

**Response 1 - GPU Warming Up**: `200 OK`

```json
{
  "status": "warming_up",
  "message": "GPU is starting up. Please retry in a moment.",
  "data": {
    "eta_seconds": 15,
    "retry_after": 15
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response 2 - Success**: `200 OK`

```json
{
  "status": "success",
  "message": "Logo generated successfully",
  "data": {
    "image_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
    "width": 512,
    "height": 512,
    "inference_time_ms": 1234.56
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Example**:
```bash
curl -X POST http://localhost:8080/generate-logo \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A modern tech startup logo with blue gradient",
    "width": 512,
    "height": 512,
    "num_inference_steps": 20
  }'
```

**Python Example**:
```python
import httpx
import asyncio

async def generate_logo():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8080/generate-logo",
            json={
                "prompt": "A minimalist coffee shop logo",
                "width": 512,
                "height": 512,
                "num_inference_steps": 20,
            },
            timeout=30.0,
        )
        return response.json()

result = asyncio.run(generate_logo())
print(result)
```

---

## Error Responses

### 400 Bad Request

Invalid request parameters.

```json
{
  "detail": [
    {
      "loc": ["body", "prompt"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 429 Too Many Requests

Rate limit exceeded.

```json
{
  "status": "error",
  "message": "Rate limit exceeded. Please try again later.",
  "data": null
}
```

### 500 Internal Server Error

Server error occurred.

```json
{
  "detail": "Logo generation failed: Connection timeout"
}
```

---

## Rate Limiting

- **Limit**: 60 requests per minute per IP address
- **Response**: HTTP 429 when exceeded
- **Reset**: Rolling 60-second window

---

## CORS

CORS is enabled for all origins by default (`*`).

For production, configure specific origins:
```bash
fly secrets set CORS_ORIGINS="https://yourdomain.com,https://app.yourdomain.com"
```

---

## Interactive Documentation

FastAPI provides automatic interactive documentation:

- **Swagger UI**: `http://localhost:8080/docs`
- **ReDoc**: `http://localhost:8080/redoc`

---

## Client Integration Examples

### JavaScript/TypeScript

```typescript
async function generateLogo(prompt: string) {
  const response = await fetch('http://localhost:8080/generate-logo', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      prompt,
      width: 512,
      height: 512,
      num_inference_steps: 20,
    }),
  });
  
  const result = await response.json();
  
  if (result.status === 'warming_up') {
    // Wait and retry
    await new Promise(resolve => setTimeout(resolve, result.data.eta_seconds * 1000));
    return generateLogo(prompt);
  }
  
  return result;
}
```

### Flutter/Dart

```dart
import 'package:http/http.dart' as http;
import 'dart:convert';

Future<Map<String, dynamic>> generateLogo(String prompt) async {
  final response = await http.post(
    Uri.parse('http://localhost:8080/generate-logo'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({
      'prompt': prompt,
      'width': 512,
      'height': 512,
      'num_inference_steps': 20,
    }),
  );
  
  final result = jsonDecode(response.body);
  
  if (result['status'] == 'warming_up') {
    await Future.delayed(Duration(seconds: result['data']['eta_seconds']));
    return generateLogo(prompt);
  }
  
  return result;
}
```

---

## Best Practices

1. **Handle warming_up status**: Always implement retry logic
2. **Use request_id**: Track requests for debugging
3. **Set timeouts**: Use appropriate client timeouts (30-60s)
4. **Cache results**: Cache generated images on client side
5. **Error handling**: Handle all error responses gracefully
6. **Rate limiting**: Implement client-side rate limiting
7. **Monitor**: Track response times and error rates

