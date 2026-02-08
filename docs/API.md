# REST API Documentation

GraphCMDB provides a REST API for CRUD operations on all node types. All endpoints return JSON responses.

## Base URL

All API endpoints are prefixed with `/api/`

## Authentication

Currently, the API uses Django's session authentication. For production use, consider implementing token-based authentication (e.g., JWT or API keys).

## Endpoints

### List Node Types

Get all registered node types/labels in the system.

**Request:**
```
GET /api/types/
```

**Response:**
```json
{
  "success": true,
  "types": [
    {
      "label": "Device",
      "display_name": "Device",
      "category": "Data Center",
      "description": "Physical or virtual device",
      "properties": ["name", "status", "serial_number"],
      "required": ["name"],
      "relationships": {
        "LOCATED_IN": {
          "target": "Room",
          "direction": "out"
        }
      }
    }
  ],
  "count": 42
}
```

### List Nodes

Get all nodes of a specific type.

**Request:**
```
GET /api/nodes/<label>/?limit=100&skip=0
```

**Query Parameters:**
- `limit` (optional): Maximum number of results (default: 100)
- `skip` (optional): Number of results to skip for pagination (default: 0)

**Response:**
```json
{
  "success": true,
  "label": "Device",
  "nodes": [
    {
      "id": "4:abc123...",
      "properties": {
        "name": "Server-01",
        "status": "active",
        "serial_number": "SN12345"
      }
    }
  ],
  "count": 25,
  "limit": 100,
  "skip": 0
}
```

### Get Node

Get a specific node by its element ID.

**Request:**
```
GET /api/nodes/<label>/<element_id>/
```

**Response:**
```json
{
  "success": true,
  "node": {
    "id": "4:abc123...",
    "label": "Device",
    "properties": {
      "name": "Server-01",
      "status": "active"
    },
    "relationships": {
      "outgoing": {
        "LOCATED_IN": [
          {
            "target_id": "4:xyz789...",
            "target_label": "Room",
            "target_name": "DC-Room-101"
          }
        ]
      },
      "incoming": {}
    }
  }
}
```

### Create Node

Create a new node of the specified type.

**Request:**
```
POST /api/nodes/<label>/
Content-Type: application/json

{
  "properties": {
    "name": "Server-01",
    "status": "active",
    "serial_number": "SN12345"
  }
}
```

**Response:**
```json
{
  "success": true,
  "node": {
    "id": "4:abc123...",
    "label": "Device",
    "properties": {
      "name": "Server-01",
      "status": "active",
      "serial_number": "SN12345"
    }
  }
}
```

**Status Codes:**
- `201 Created`: Node created successfully
- `400 Bad Request`: Missing required properties or invalid JSON
- `404 Not Found`: Unknown node type
- `500 Internal Server Error`: Server error

### Update Node

Update an existing node (supports both PUT and PATCH methods).

**Request:**
```
PUT /api/nodes/<label>/<element_id>/
Content-Type: application/json

{
  "properties": {
    "status": "maintenance"
  }
}
```

**Response:**
```json
{
  "success": true,
  "node": {
    "id": "4:abc123...",
    "label": "Device",
    "properties": {
      "name": "Server-01",
      "status": "maintenance",
      "serial_number": "SN12345"
    }
  }
}
```

**Status Codes:**
- `200 OK`: Node updated successfully
- `400 Bad Request`: Invalid JSON
- `404 Not Found`: Node or node type not found
- `500 Internal Server Error`: Server error

### Delete Node

Delete a node.

**Request:**
```
DELETE /api/nodes/<label>/<element_id>/
```

**Response:**
```json
{
  "success": true,
  "message": "Node deleted successfully"
}
```

**Status Codes:**
- `200 OK`: Node deleted successfully
- `404 Not Found`: Node or node type not found
- `500 Internal Server Error`: Server error

### Create Relationship

Create a relationship between two nodes.

**Request:**
```
POST /api/nodes/<label>/<element_id>/relationships/
Content-Type: application/json

{
  "relationship_type": "LOCATED_IN",
  "target_label": "Room",
  "target_id": "4:xyz789..."
}
```

**Response:**
```json
{
  "success": true,
  "message": "Relationship created successfully"
}
```

**Status Codes:**
- `201 Created`: Relationship created successfully
- `400 Bad Request`: Missing required fields or invalid relationship type
- `404 Not Found`: Source node, target node, or node type not found
- `500 Internal Server Error`: Server error

### Delete Relationship

Remove a relationship between two nodes.

**Request:**
```
DELETE /api/nodes/<label>/<element_id>/relationships/<relationship_type>/<target_id>/
```

**Response:**
```json
{
  "success": true,
  "message": "Relationship removed successfully"
}
```

**Status Codes:**
- `200 OK`: Relationship removed successfully
- `404 Not Found`: Relationship, node, or node type not found
- `500 Internal Server Error`: Server error

## Error Responses

All error responses follow this format:

```json
{
  "success": false,
  "error": "Error message describing what went wrong"
}
```

## Examples

### Using curl

**List all node types:**
```bash
curl http://localhost:8000/api/types/
```

**Create a device:**
```bash
curl -X POST http://localhost:8000/api/nodes/Device/ \
  -H "Content-Type: application/json" \
  -d '{
    "properties": {
      "name": "Server-01",
      "status": "active"
    }
  }'
```

**Get a specific device:**
```bash
curl http://localhost:8000/api/nodes/Device/4:abc123.../
```

**Update a device:**
```bash
curl -X PUT http://localhost:8000/api/nodes/Device/4:abc123.../ \
  -H "Content-Type: application/json" \
  -d '{
    "properties": {
      "status": "maintenance"
    }
  }'
```

**Delete a device:**
```bash
curl -X DELETE http://localhost:8000/api/nodes/Device/4:abc123.../
```

**Create a relationship:**
```bash
curl -X POST http://localhost:8000/api/nodes/Device/4:abc123.../relationships/ \
  -H "Content-Type: application/json" \
  -d '{
    "relationship_type": "LOCATED_IN",
    "target_label": "Room",
    "target_id": "4:xyz789..."
  }'
```

### Using Python requests

```python
import requests

base_url = "http://localhost:8000/api"

# List node types
response = requests.get(f"{base_url}/types/")
types = response.json()

# Create a node
response = requests.post(
    f"{base_url}/nodes/Device/",
    json={
        "properties": {
            "name": "Server-01",
            "status": "active"
        }
    }
)
node = response.json()
node_id = node['node']['id']

# Get the node
response = requests.get(f"{base_url}/nodes/Device/{node_id}/")
node = response.json()

# Update the node
response = requests.put(
    f"{base_url}/nodes/Device/{node_id}/",
    json={
        "properties": {
            "status": "maintenance"
        }
    }
)

# Delete the node
response = requests.delete(f"{base_url}/nodes/Device/{node_id}/")
```

## CSRF Protection

For POST, PUT, PATCH, and DELETE requests, CSRF protection is currently disabled using the `@csrf_exempt` decorator for API endpoints. In production, you should implement proper authentication and authorization mechanisms.

## Audit Logging

All API operations (create, update, delete, connect, disconnect) are logged in the audit log if the audit_log_pack feature pack is enabled.
