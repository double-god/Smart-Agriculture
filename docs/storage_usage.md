# StorageService Usage Guide

This guide explains how to use the StorageService for file upload operations in the Smart-Agriculture system.

## Overview

StorageService is a singleton service that encapsulates MinIO object storage operations. It provides:

- Automatic MinIO client initialization
- Bucket auto-creation with public read policy
- Simple file upload API with URL generation
- Centralized error handling

## Basic Usage

### Getting the Service Instance

```python
from app.services.storage import get_storage_service

# Get the singleton instance
storage = get_storage_service()

# Access bucket name
print(f"Bucket: {storage.bucket_name}")  # Output: Bucket: smart-agriculture
```

### Uploading a File

```python
from app.services.storage import get_storage_service

storage = get_storage_service()

# Upload a file
with open("photo.jpg", "rb") as f:
    url = storage.upload_image(f, "diagnosis_123.jpg")
    print(f"Uploaded to: {url}")
    # Output: Uploaded to: http://localhost:9010/smart-agriculture/diagnosis_123.jpg
```

### Uploading with Custom Content Type

```python
from app.services.storage import get_storage_service

storage = get_storage_service()

# Upload PNG file with correct content type
with open("image.png", "rb") as f:
    url = storage.upload_image(f, "diagnosis_456.png", content_type="image/png")
    print(f"Uploaded to: {url}")
```

## FastAPI Integration

### Using Dependency Injection

```python
from fastapi import APIRouter, Depends, UploadFile
from app.core import depends_storage
from app.services.storage import StorageService

router = APIRouter()

@router.post("/upload")
async def upload_diagnosis_image(
    file: UploadFile,
    storage: StorageService = Depends(depends_storage)
):
    """
    Upload a diagnosis image to MinIO storage.

    Returns:
        JSON with the public URL of the uploaded file
    """
    url = storage.upload_image(
        file.file,
        file.filename,
        content_type=file.content_type
    )

    return {
        "filename": file.filename,
        "url": url,
        "message": "File uploaded successfully"
    }
```

### Complete Example with Diagnosis

```python
from fastapi import APIRouter, Depends, UploadFile, HTTPException
from app.core import depends_storage, depends_taxonomy
from app.services.storage import StorageService
from app.services.taxonomy_service import TaxonomyService

router = APIRouter()

@router.post("/diagnosis/{diagnosis_id}/image")
async def upload_diagnosis_image(
    diagnosis_id: int,
    file: UploadFile,
    storage: StorageService = Depends(depends_storage),
    taxonomy: TaxonomyService = Depends(depends_taxonomy)
):
    """
    Upload an image for a specific diagnosis.

    The image filename will include the diagnosis ID for organization.
    """
    # Validate diagnosis exists
    try:
        entry = taxonomy.get_by_id(diagnosis_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Diagnosis {diagnosis_id} not found")

    # Generate unique filename with diagnosis ID
    filename = f"diagnosis_{diagnosis_id}_{file.filename}"

    # Upload to MinIO
    url = storage.upload_image(
        file.file,
        filename,
        content_type=file.content_type or "image/jpeg"
    )

    return {
        "diagnosis_id": diagnosis_id,
        "diagnosis_name": entry.zh_scientific_name,
        "filename": filename,
        "url": url
    }
```

## Error Handling

### Handling Connection Errors

```python
from app.services.storage import get_storage_service, StorageConnectionError

try:
    storage = get_storage_service()
    # ... use storage
except StorageConnectionError as e:
    print(f"Storage connection failed: {e}")
    # Handle error: log, alert, return error response
```

### Error Handling in FastAPI

```python
from fastapi import APIRouter, Depends, UploadFile, HTTPException
from app.services.storage import StorageService, StorageConnectionError

@router.post("/upload")
async def upload_file(
    file: UploadFile,
    storage: StorageService = Depends(depends_storage)
):
    try:
        url = storage.upload_image(file.file, file.filename)
        return {"url": url}

    except StorageConnectionError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Storage service unavailable: {str(e)}"
        )
```

## Configuration

StorageService reads configuration from environment variables via `app.core.config.Settings`:

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `MINIO_ENDPOINT` | MinIO server address | `localhost:9000` |
| `MINIO_ACCESS_KEY` | MinIO access key | (empty) |
| `MINIO_SECRET_KEY` | MinIO secret key | (empty) |
| `MINIO_BUCKET_NAME` | Bucket name | `smart-agriculture` |
| `MINIO_SECURE` | Use HTTPS (true/false) | `false` |

Example `.env` file:

```env
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=12345678
MINIO_BUCKET_NAME=smart-agriculture
MINIO_SECURE=false
```

## URL Format

Uploaded files are accessible via public URLs in the format:

```
http://{endpoint}/{bucket}/{filename}
```

Examples:
- `http://localhost:9010/smart-agriculture/diagnosis_123.jpg`
- `http://minio:9000/smart-agriculture/test.png`

**Note**: For production use, consider implementing presigned URLs for better security.

## Best Practices

### 1. Unique Filenames

Always ensure filenames are unique to avoid overwriting:

```python
import uuid

# Add UUID prefix to ensure uniqueness
unique_filename = f"{uuid.uuid4()}_{original_filename}"
url = storage.upload_image(file.file, unique_filename)
```

### 2. Content Type Validation

Always specify the correct content type:

```python
# Supported image content types
content_types = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp"
}

# Get file extension and set content type
import os
ext = os.path.splitext(filename)[1].lower()
content_type = content_types.get(ext, "image/jpeg")
```

### 3. Error Recovery

Implement retry logic for transient failures:

```python
import time
from app.services.storage import StorageConnectionError

def upload_with_retry(storage, file_data, filename, max_retries=3):
    for attempt in range(max_retries):
        try:
            return storage.upload_image(file_data, filename)
        except StorageConnectionError as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff
```

## Testing

### Mocking StorageService in Tests

```python
from unittest.mock import Mock, patch
from app.services.storage import StorageService

def test_upload_endpoint():
    # Mock the storage service
    mock_storage = Mock(spec=StorageService)
    mock_storage.upload_image.return_value = "http://test.com/file.jpg"

    # Use mock in dependency override
    from fastapi.testclient import TestClient
    from app.main import app

    app.dependency_overrides[depends_storage] = lambda: mock_storage

    client = TestClient(app)
    response = client.post("/upload", files={"file": ...})

    assert response.status_code == 200
    mock_storage.upload_image.assert_called_once()
```

## Troubleshooting

### Connection Refused

**Error**: `Failed to connect to MinIO at minio:9000`

**Solutions**:
1. Ensure MinIO is running: `docker-compose up minio`
2. Check `MINIO_ENDPOINT` in `.env`
3. Verify network connectivity

### Authentication Failed

**Error**: `Access Denied` or `403 Forbidden`

**Solutions**:
1. Verify `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY` in `.env`
2. Check MinIO logs for authentication errors
3. Ensure access credentials match MinIO configuration

### Bucket Creation Failed

**Error**: `Failed to create or configure bucket`

**Solutions**:
1. Check MinIO disk space
2. Verify bucket name doesn't contain invalid characters
3. Ensure proper permissions for bucket creation

## Future Enhancements

Planned features for future versions:

- **Presigned URLs**: Generate temporary signed URLs for better security
- **File Deletion**: Add `delete_file()` method for cleanup
- **Batch Upload**: Support uploading multiple files at once
- **Async API**: Migrate to async MinIO client for better performance
- **CDN Integration**: Support CDN URL generation for static assets
- **File Metadata**: Store and retrieve file metadata (size, type, upload time)

## Related Documentation

- [TaxonomyService Usage](./taxonomy_usage.md)
- [FastAPI Dependencies](../app/core/deps.py)
- [MinIO Python SDK](https://github.com/minio/minio-py)
