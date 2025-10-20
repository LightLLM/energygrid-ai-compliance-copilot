# EnergyGrid.AI API Reference

This document provides detailed API reference for the EnergyGrid.AI Compliance Copilot system.

## Base URL

```
https://{api-gateway-id}.execute-api.{region}.amazonaws.com/{stage}
```

## Authentication

All API endpoints require authentication using AWS Cognito JWT tokens. Include the token in the Authorization header:

```http
Authorization: Bearer <jwt-token>
```

### Getting a JWT Token

1. **Using AWS CLI**:
```bash
aws cognito-idp initiate-auth \
    --auth-flow USER_PASSWORD_AUTH \
    --client-id <client-id> \
    --auth-parameters USERNAME=<username>,PASSWORD=<password>
```

2. **Using the Web Interface**: Login through the Streamlit application to get a token.

## Error Handling

All endpoints return consistent error responses with the following structure:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "specific_field",
      "value": "invalid_value"
    },
    "timestamp": "2024-01-01T12:00:00Z",
    "request_id": "req-123456"
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `UNAUTHORIZED` | 401 | Authentication required |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource already exists |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Internal server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

## Endpoints

### Documents

#### Upload Document

Upload a PDF document for compliance analysis.

```http
POST /documents/upload
```

**Headers:**
- `Content-Type: multipart/form-data`
- `Authorization: Bearer <jwt-token>`

**Request Body:**
```
file: <pdf-file> (required)
metadata: {
  "title": "Document Title",
  "source": "Regulatory Body",
  "effective_date": "2024-01-01",
  "document_type": "regulation",
  "tags": ["energy", "compliance"]
}
```

**Response (201 Created):**
```json
{
  "document_id": "doc-123456789",
  "filename": "regulation.pdf",
  "size": 2048576,
  "status": "uploaded",
  "upload_timestamp": "2024-01-01T12:00:00Z",
  "processing_eta": "2024-01-01T12:05:00Z",
  "message": "Document uploaded successfully and queued for processing"
}
```

**Validation Rules:**
- File must be PDF format
- Maximum file size: 50MB
- Filename must not contain special characters
- Title is required in metadata

#### Get Document Status

Get the processing status of a document.

```http
GET /documents/{document_id}/status
```

**Path Parameters:**
- `document_id` (string, required): Unique document identifier

**Response (200 OK):**
```json
{
  "document_id": "doc-123456789",
  "filename": "regulation.pdf",
  "status": "processing",
  "stage": "analysis",
  "progress": 75,
  "stages": {
    "upload": {
      "status": "completed",
      "timestamp": "2024-01-01T12:00:00Z"
    },
    "analysis": {
      "status": "in_progress",
      "timestamp": "2024-01-01T12:01:00Z",
      "progress": 75
    },
    "planning": {
      "status": "pending",
      "timestamp": null
    },
    "completion": {
      "status": "pending",
      "timestamp": null
    }
  },
  "estimated_completion": "2024-01-01T12:05:00Z",
  "error": null
}
```

**Status Values:**
- `uploaded`: Document uploaded, waiting for processing
- `processing`: Document is being processed
- `completed`: Processing completed successfully
- `failed`: Processing failed with errors

### Obligations

#### List Obligations

Retrieve a list of extracted compliance obligations.

```http
GET /obligations
```

**Query Parameters:**
- `document_id` (string, optional): Filter by document ID
- `category` (string, optional): Filter by category (`reporting`, `monitoring`, `operational`, `financial`)
- `severity` (string, optional): Filter by severity (`critical`, `high`, `medium`, `low`)
- `deadline_type` (string, optional): Filter by deadline type (`recurring`, `one-time`, `ongoing`)
- `search` (string, optional): Search in obligation descriptions
- `limit` (integer, optional, default: 50): Number of results per page
- `offset` (integer, optional, default: 0): Number of results to skip
- `sort_by` (string, optional, default: `created_timestamp`): Sort field
- `sort_order` (string, optional, default: `desc`): Sort order (`asc`, `desc`)

**Response (200 OK):**
```json
{
  "obligations": [
    {
      "obligation_id": "obl-123456789",
      "document_id": "doc-123456789",
      "description": "Submit quarterly compliance report to regulatory authority within 30 days of quarter end",
      "category": "reporting",
      "severity": "high",
      "deadline_type": "recurring",
      "applicable_entities": ["transmission_operators", "distribution_companies"],
      "extracted_text": "Original text from document...",
      "confidence_score": 0.95,
      "created_timestamp": "2024-01-01T12:02:00Z",
      "tags": ["quarterly", "reporting", "deadline"]
    }
  ],
  "pagination": {
    "total": 150,
    "limit": 50,
    "offset": 0,
    "has_more": true
  },
  "filters": {
    "category": "reporting",
    "severity": "high"
  }
}
```

#### Get Obligation Details

Get detailed information about a specific obligation.

```http
GET /obligations/{obligation_id}
```

**Path Parameters:**
- `obligation_id` (string, required): Unique obligation identifier

**Response (200 OK):**
```json
{
  "obligation_id": "obl-123456789",
  "document_id": "doc-123456789",
  "description": "Submit quarterly compliance report to regulatory authority within 30 days of quarter end",
  "category": "reporting",
  "severity": "high",
  "deadline_type": "recurring",
  "applicable_entities": ["transmission_operators", "distribution_companies"],
  "extracted_text": "Companies operating transmission facilities must submit...",
  "confidence_score": 0.95,
  "created_timestamp": "2024-01-01T12:02:00Z",
  "updated_timestamp": "2024-01-01T12:02:00Z",
  "tags": ["quarterly", "reporting", "deadline"],
  "related_obligations": ["obl-987654321", "obl-456789123"],
  "generated_tasks": ["task-123456789", "task-987654321"]
}
```

### Tasks

#### List Tasks

Retrieve a list of generated audit tasks.

```http
GET /tasks
```

**Query Parameters:**
- `obligation_id` (string, optional): Filter by obligation ID
- `assigned_to` (string, optional): Filter by assigned user
- `status` (string, optional): Filter by status (`pending`, `in_progress`, `completed`, `overdue`)
- `priority` (string, optional): Filter by priority (`high`, `medium`, `low`)
- `due_date_from` (string, optional): Filter tasks due after this date (ISO 8601)
- `due_date_to` (string, optional): Filter tasks due before this date (ISO 8601)
- `search` (string, optional): Search in task titles and descriptions
- `limit` (integer, optional, default: 50): Number of results per page
- `offset` (integer, optional, default: 0): Number of results to skip
- `sort_by` (string, optional, default: `due_date`): Sort field
- `sort_order` (string, optional, default: `asc`): Sort order (`asc`, `desc`)

**Response (200 OK):**
```json
{
  "tasks": [
    {
      "task_id": "task-123456789",
      "obligation_id": "obl-123456789",
      "title": "Prepare Q1 2024 Compliance Report",
      "description": "Compile quarterly compliance data and prepare report for submission to regulatory authority",
      "priority": "high",
      "status": "pending",
      "assigned_to": "user123",
      "assigned_by": "manager456",
      "due_date": "2024-04-30T23:59:59Z",
      "created_timestamp": "2024-01-01T12:03:00Z",
      "updated_timestamp": "2024-01-01T12:03:00Z",
      "estimated_hours": 8,
      "tags": ["quarterly", "reporting"],
      "dependencies": ["task-987654321"]
    }
  ],
  "pagination": {
    "total": 25,
    "limit": 50,
    "offset": 0,
    "has_more": false
  },
  "summary": {
    "pending": 15,
    "in_progress": 8,
    "completed": 2,
    "overdue": 0
  }
}
```

#### Update Task

Update task details or status.

```http
PUT /tasks/{task_id}
```

**Path Parameters:**
- `task_id` (string, required): Unique task identifier

**Request Body:**
```json
{
  "status": "in_progress",
  "assigned_to": "user456",
  "due_date": "2024-05-15T23:59:59Z",
  "notes": "Started working on data collection",
  "progress": 25
}
```

**Response (200 OK):**
```json
{
  "task_id": "task-123456789",
  "status": "in_progress",
  "updated_timestamp": "2024-01-01T14:00:00Z",
  "message": "Task updated successfully"
}
```

### Reports

#### Generate Report

Request generation of a compliance report.

```http
POST /reports/generate
```

**Request Body:**
```json
{
  "report_type": "compliance_summary",
  "title": "Q1 2024 Compliance Summary",
  "date_range": {
    "start_date": "2024-01-01",
    "end_date": "2024-03-31"
  },
  "filters": {
    "categories": ["reporting", "monitoring"],
    "severities": ["high", "critical"],
    "document_ids": ["doc-123456789"],
    "tags": ["quarterly"]
  },
  "format": "pdf",
  "include_charts": true,
  "include_recommendations": true
}
```

**Report Types:**
- `compliance_summary`: Overview of compliance status
- `audit_readiness`: Audit preparation report
- `obligation_status`: Status of all obligations
- `task_progress`: Task completion report
- `risk_assessment`: Risk analysis report

**Response (202 Accepted):**
```json
{
  "report_id": "rpt-123456789",
  "status": "generating",
  "estimated_completion": "2024-01-01T12:35:00Z",
  "message": "Report generation started"
}
```

#### Get Report Status

Check the status of report generation.

```http
GET /reports/{report_id}/status
```

**Path Parameters:**
- `report_id` (string, required): Unique report identifier

**Response (200 OK):**
```json
{
  "report_id": "rpt-123456789",
  "status": "completed",
  "progress": 100,
  "generated_timestamp": "2024-01-01T12:33:00Z",
  "file_size": 1048576,
  "page_count": 25,
  "download_url": "https://s3.amazonaws.com/reports-bucket/rpt-123456789.pdf?signed-url",
  "expires_at": "2024-01-01T18:33:00Z"
}
```

#### Download Report

Download a generated report.

```http
GET /reports/{report_id}
```

**Path Parameters:**
- `report_id` (string, required): Unique report identifier

**Response (200 OK):**
- Content-Type: `application/pdf`
- Content-Disposition: `attachment; filename="compliance-report.pdf"`
- Binary PDF content

#### List Reports

Get a list of generated reports.

```http
GET /reports
```

**Query Parameters:**
- `report_type` (string, optional): Filter by report type
- `status` (string, optional): Filter by status (`generating`, `completed`, `failed`)
- `generated_by` (string, optional): Filter by user who generated the report
- `date_from` (string, optional): Filter reports generated after this date
- `date_to` (string, optional): Filter reports generated before this date
- `limit` (integer, optional, default: 20): Number of results per page
- `offset` (integer, optional, default: 0): Number of results to skip

**Response (200 OK):**
```json
{
  "reports": [
    {
      "report_id": "rpt-123456789",
      "title": "Q1 2024 Compliance Summary",
      "report_type": "compliance_summary",
      "status": "completed",
      "generated_by": "user123",
      "generated_timestamp": "2024-01-01T12:33:00Z",
      "file_size": 1048576,
      "page_count": 25
    }
  ],
  "pagination": {
    "total": 10,
    "limit": 20,
    "offset": 0,
    "has_more": false
  }
}
```

## Rate Limits

API endpoints are subject to rate limiting to ensure fair usage:

| Endpoint | Rate Limit | Burst Limit |
|----------|------------|-------------|
| `/documents/upload` | 10 requests/minute | 20 requests |
| `/reports/generate` | 5 requests/minute | 10 requests |
| All other GET endpoints | 100 requests/minute | 200 requests |
| All other POST/PUT endpoints | 50 requests/minute | 100 requests |

Rate limit headers are included in all responses:
- `X-RateLimit-Limit`: Request limit per time window
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Time when the rate limit resets (Unix timestamp)

## Webhooks

The system can send webhook notifications for important events:

### Webhook Events

- `document.uploaded`: Document successfully uploaded
- `document.processed`: Document processing completed
- `document.failed`: Document processing failed
- `report.generated`: Report generation completed
- `task.created`: New task created
- `task.updated`: Task status updated

### Webhook Payload

```json
{
  "event": "document.processed",
  "timestamp": "2024-01-01T12:05:00Z",
  "data": {
    "document_id": "doc-123456789",
    "status": "completed",
    "obligations_count": 15,
    "tasks_count": 8
  }
}
```

## SDK Examples

### Python

```python
import requests
import json

class EnergyGridAPI:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def upload_document(self, file_path, metadata=None):
        url = f"{self.base_url}/documents/upload"
        files = {'file': open(file_path, 'rb')}
        data = {'metadata': json.dumps(metadata or {})}
        
        response = requests.post(url, files=files, data=data, 
                               headers={'Authorization': self.headers['Authorization']})
        return response.json()
    
    def get_obligations(self, **filters):
        url = f"{self.base_url}/obligations"
        response = requests.get(url, params=filters, headers=self.headers)
        return response.json()
    
    def generate_report(self, report_config):
        url = f"{self.base_url}/reports/generate"
        response = requests.post(url, json=report_config, headers=self.headers)
        return response.json()

# Usage
api = EnergyGridAPI('https://api.energygrid.ai', 'your-jwt-token')
result = api.upload_document('regulation.pdf', {'title': 'New Regulation'})
```

### JavaScript

```javascript
class EnergyGridAPI {
    constructor(baseUrl, token) {
        this.baseUrl = baseUrl;
        this.headers = {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        };
    }
    
    async uploadDocument(file, metadata = {}) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('metadata', JSON.stringify(metadata));
        
        const response = await fetch(`${this.baseUrl}/documents/upload`, {
            method: 'POST',
            headers: {
                'Authorization': this.headers.Authorization
            },
            body: formData
        });
        
        return response.json();
    }
    
    async getObligations(filters = {}) {
        const params = new URLSearchParams(filters);
        const response = await fetch(`${this.baseUrl}/obligations?${params}`, {
            headers: this.headers
        });
        
        return response.json();
    }
    
    async generateReport(reportConfig) {
        const response = await fetch(`${this.baseUrl}/reports/generate`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify(reportConfig)
        });
        
        return response.json();
    }
}

// Usage
const api = new EnergyGridAPI('https://api.energygrid.ai', 'your-jwt-token');
const result = await api.uploadDocument(file, {title: 'New Regulation'});
```

## Testing

### Postman Collection

A Postman collection is available for testing all API endpoints:

```bash
# Import the collection
curl -o energygrid-api.postman_collection.json \
  https://raw.githubusercontent.com/your-org/energygrid-ai-compliance-copilot/main/docs/postman/collection.json
```

### cURL Examples

```bash
# Upload document
curl -X POST "https://api.energygrid.ai/documents/upload" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -F "file=@regulation.pdf" \
  -F 'metadata={"title":"Test Regulation"}'

# Get obligations
curl -X GET "https://api.energygrid.ai/obligations?category=reporting&limit=10" \
  -H "Authorization: Bearer $JWT_TOKEN"

# Generate report
curl -X POST "https://api.energygrid.ai/reports/generate" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "report_type": "compliance_summary",
    "date_range": {
      "start_date": "2024-01-01",
      "end_date": "2024-03-31"
    }
  }'
```

## Support

For API support and questions:
- **Documentation**: [API Reference](https://docs.energygrid.ai/api)
- **Issues**: [GitHub Issues](https://github.com/your-org/energygrid-ai-compliance-copilot/issues)
- **Email**: api-support@energygrid.ai