# API Documentation

This document describes the REST API endpoints provided by the FitGirl Updater application.

## Base URL

All API endpoints are relative to the base URL: `http://localhost:2121`

## Authentication

Currently, the API does not require authentication. All endpoints are publicly accessible.

## Response Format

All API responses are in JSON format with the following structure:

```json
{
  "success": true|false,
  "data": {...},
  "error": "error message",
  "message": "success message"
}
```

## Endpoints

### 1. Get Releases

**GET** `/api/releases`

Retrieve releases with filtering, sorting, and pagination.

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number (1-based) |
| `limit` | integer | 50 | Number of releases per page |
| `search` | string | "" | Search term for title |
| `status` | string | "" | Filter by status (NEW, DOWNLOADED, IGNORED) |
| `sort` | string | "date_desc" | Sort order (date_desc, date_asc, title_asc, title_desc) |

#### Example Request

```bash
curl "http://localhost:2121/api/releases?page=1&limit=20&search=cyberpunk&status=NEW"
```

#### Example Response

```json
{
  "success": true,
  "releases": [
    {
      "id": 1,
      "url": "https://1337x.to/torrent/123456/",
      "title": "Cyberpunk 2077 v2.0",
      "description": "Full game description...",
      "short_description": "Short description...",
      "publish_date": "2024-01-15",
      "game_release_date": "2020-12-10",
      "size": "45.2 GB",
      "status": "NEW",
      "status_text": "New",
      "status_color": "#28a745",
      "has_download_links": true,
      "image_count": 5,
      "magnet_link": "magnet:?xt=urn:btih:...",
      "cover_image_url": "https://...",
      "screenshot_urls": ["https://...", "https://..."]
    }
  ],
  "total": 150,
  "filtered_total": 25,
  "page": 1,
  "limit": 20,
  "has_more": true
}
```

### 2. Start Synchronization

**POST** `/api/sync`

Start the synchronization process to fetch new releases from 1337x.

#### Request Body

No body required.

#### Example Request

```bash
curl -X POST "http://localhost:2121/api/sync"
```

#### Example Response

```json
{
  "success": true,
  "message": "Synchronization started in background",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 3. Get Synchronization Status

**GET** `/api/sync/status`

Get the current status of the synchronization process.

#### Example Request

```bash
curl "http://localhost:2121/api/sync/status"
```

#### Example Response

```json
{
  "success": true,
  "sync_in_progress": false,
  "progress": {
    "status": "completed",
    "current_page": 100,
    "total_pages": 100,
    "current_release": 50,
    "total_releases": 50,
    "new_releases": 15,
    "updated_releases": 5,
    "message": "Synchronization completed: 15 new, 5 updated, 30 skipped"
  }
}
```

### 4. Get Statistics

**GET** `/api/statistics`

Get release statistics and counts.

#### Example Request

```bash
curl "http://localhost:2121/api/statistics"
```

#### Example Response

```json
{
  "success": true,
  "statistics": {
    "total_releases": 150,
    "new_releases": 45,
    "downloaded_releases": 80,
    "ignored_releases": 25,
    "status_counts": {
      "NEW": 45,
      "DOWNLOADED": 80,
      "IGNORED": 25
    },
    "last_sync": "2024-01-15T10:30:00Z"
  }
}
```

### 5. Update Release Status

**PUT** `/api/releases/{release_id}/status`

Update the status of a specific release.

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `release_id` | integer | ID of the release to update |

#### Request Body

```json
{
  "status": "DOWNLOADED"
}
```

#### Status Values

- `NEW`: New release
- `DOWNLOADED`: Marked as downloaded
- `IGNORED`: Marked as ignored

#### Example Request

```bash
curl -X PUT "http://localhost:2121/api/releases/123/status" \
  -H "Content-Type: application/json" \
  -d '{"status": "DOWNLOADED"}'
```

#### Example Response

```json
{
  "success": true,
  "message": "Status updated successfully"
}
```

### 6. Delete Release

**DELETE** `/api/releases/{release_id}`

Delete a specific release from the database.

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `release_id` | integer | ID of the release to delete |

#### Example Request

```bash
curl -X DELETE "http://localhost:2121/api/releases/123"
```

#### Example Response

```json
{
  "success": true,
  "message": "Release deleted successfully"
}
```

### 7. Clear All Releases

**POST** `/api/releases/clear`

Clear all releases from the database.

#### Request Body

```json
{
  "confirm": true
}
```

#### Example Request

```bash
curl -X POST "http://localhost:2121/api/releases/clear" \
  -H "Content-Type: application/json" \
  -d '{"confirm": true}'
```

#### Example Response

```json
{
  "success": true,
  "message": "All releases cleared successfully"
}
```

### 8. Sync Single Release

**POST** `/api/releases/{release_id}/sync`

Re-scrape a single release to update its information.

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `release_id` | integer | ID of the release to sync |

#### Example Request

```bash
curl -X POST "http://localhost:2121/api/releases/123/sync"
```

#### Example Response

```json
{
  "success": true,
  "message": "Release synced successfully: Cyberpunk 2077 v2.0",
  "release": {
    "id": 123,
    "title": "Cyberpunk 2077 v2.0",
    "description": "Updated description...",
    "size": "45.2 GB",
    "status": "NEW",
    "magnet_link": "magnet:?xt=urn:btih:...",
    "screenshot_urls": ["https://...", "https://..."]
  }
}
```

### 9. Get Configuration

**GET** `/api/config`

Get application configuration information.

#### Example Request

```bash
curl "http://localhost:2121/api/config"
```

#### Example Response

```json
{
  "success": true,
  "config": {
    "version": "0.1.0",
    "debug_mode": false,
    "web_port": 2121,
          "max_concurrent_requests": 5,
      "timeout": 30,
    
    "last_sync_check": "2024-01-15T10:30:00Z",
    "last_update_check": "2024-01-15T10:30:00Z"
  }
}
```

## WebSocket Events

The application also provides real-time updates via WebSocket connections.

### Connection

Connect to WebSocket at: `ws://localhost:2121/socket.io/`

### Events

#### 1. Connect

**Event**: `connect`

Emitted when client connects to WebSocket.

#### 2. Sync Progress

**Event**: `sync_progress`

Emitted during synchronization to show progress.

```json
{
  "status": "scraping",
  "current_page": 25,
  "total_pages": 100,
  "message": "Scraping page 25 of 100",
  "new_releases": 10,
  "updated_releases": 2
}
```

#### 3. New Release Added

**Event**: `new_release_added`

Emitted when a new release is added during synchronization.

```json
{
  "success": true,
  "release": {
    "id": 124,
    "title": "New Game v1.0",
    "description": "Game description...",
    "status": "NEW",
    "magnet_link": "magnet:?xt=urn:btih:...",
    "screenshot_urls": ["https://..."]
  },
  "total_releases": 151
}
```

## Error Handling

### HTTP Status Codes

- `200 OK`: Request successful
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

### Error Response Format

```json
{
  "success": false,
  "error": "Error description"
}
```

### Common Error Messages

- `"Database not initialized"`: Database connection failed
- `"Release not found"`: Release ID doesn't exist
- `"Invalid status"`: Invalid status value provided
- `"Synchronization already in progress"`: Sync already running
- `"Confirmation required"`: Confirmation required for destructive actions

## Rate Limiting

Currently, no rate limiting is implemented. However, it's recommended to:

- Limit requests to reasonable frequency
- Use WebSocket for real-time updates instead of polling
- Implement proper error handling and retry logic

## CORS

The API supports CORS for cross-origin requests. All origins are allowed by default.

## Examples

### JavaScript/Fetch

```javascript
// Get releases
const response = await fetch('/api/releases?page=1&limit=20');
const data = await response.json();

// Update status
const updateResponse = await fetch('/api/releases/123/status', {
  method: 'PUT',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ status: 'DOWNLOADED' })
});

// Start sync
const syncResponse = await fetch('/api/sync', {
  method: 'POST'
});
```

### Python/Requests

```python
import requests

# Get releases
response = requests.get('http://localhost:2121/api/releases', 
                      params={'page': 1, 'limit': 20})
data = response.json()

# Update status
response = requests.put('http://localhost:2121/api/releases/123/status',
                       json={'status': 'DOWNLOADED'})

# Start sync
response = requests.post('http://localhost:2121/api/sync')
```

### cURL

```bash
# Get all new releases
curl "http://localhost:2121/api/releases?status=NEW&limit=50"

# Search for specific game
curl "http://localhost:2121/api/releases?search=cyberpunk"

# Update release status
curl -X PUT "http://localhost:2121/api/releases/123/status" \
  -H "Content-Type: application/json" \
  -d '{"status": "DOWNLOADED"}'

# Start synchronization
curl -X POST "http://localhost:2121/api/sync"
```

## Versioning

API versioning is not currently implemented. All endpoints use the latest version.

## Deprecation

No endpoints are currently deprecated. Future deprecations will be announced with advance notice. 