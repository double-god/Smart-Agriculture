# Specification: Storage Service

**Capability**: Storage
**Version**: 1.0.0
**Status**: Proposed

---

## ADDED Requirements

### REQ-STORAGE-001: StorageService Singleton

The system MUST implement a singleton service in `app/services/storage.py` that encapsulates MinIO operations.

**Class Design**:

```python
from minio import Minio
from minio.error import S3Error
from app.core.config import get_settings
from typing import BinaryIO, Optional
import urllib3


class StorageConnectionError(Exception):
    """Raised when MinIO connection fails."""

    pass


class StorageService:
    """
    Singleton service for MinIO object storage operations.

    This service manages MinIO client connections and provides
    simple methods for uploading files and generating access URLs.
    """

    _instance: Optional["StorageService"] = None

    def __new__(cls) -> "StorageService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # Load configuration
        settings = get_settings()
        self._endpoint = settings.minio_endpoint
        self._access_key = settings.minio_access_key
        self._secret_key = settings.minio_secret_key
        self._bucket_name = settings.minio_bucket_name
        self._secure = settings.minio_secure

        # Disable SSL warnings for development
        if not self._secure:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Initialize MinIO client
        try:
            self._client = Minio(
                self._endpoint,
                access_key=self._access_key,
                secret_key=self._secret_key,
                secure=self._secure,
            )

            # Create bucket if not exists
            self._ensure_bucket_exists()

        except S3Error as e:
            raise StorageConnectionError(
                f"Failed to connect to MinIO at {self._endpoint}: {e}"
            )

    def _ensure_bucket_exists(self):
        """
        Ensure the bucket exists, create if not.

        Raises:
            StorageConnectionError: If bucket creation fails
        """
        try:
            if not self._client.bucket_exists(self._bucket_name):
                self._client.make_bucket(self._bucket_name)

                # Set bucket policy to public read
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": "*"},
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{self._bucket_name}/*"],
                        }
                    ],
                }

                import json

                self._client.set_bucket_policy(
                    self._bucket_name, json.dumps(policy)
                )

        except S3Error as e:
            raise StorageConnectionError(
                f"Failed to create or configure bucket '{self._bucket_name}': {e}"
            )

    def upload_image(
        self, file_data: BinaryIO, filename: str, content_type: str = "image/jpeg"
    ) -> str:
        """
        Upload an image file to MinIO and return the accessible URL.

        Args:
            file_data: File-like object containing image data
            filename: Name to save the file as in the bucket
            content_type: MIME type of the file (default: image/jpeg)

        Returns:
            Full HTTP URL to access the uploaded file

        Raises:
            StorageConnectionError: If upload fails

        Example:
            >>> with open("photo.jpg", "rb") as f:
            ...     url = storage.upload_image(f, "diagnosis_123.jpg")
            ...     print(url)
            http://localhost:9010/smart-agriculture/diagnosis_123.jpg
        """
        try:
            # Upload file
            self._client.put_object(
                bucket_name=self._bucket_name,
                object_name=filename,
                data=file_data,
                length=-1,  # Unknown size, stream until EOF
                part_size=10 * 1024 * 1024,  # 10MB parts
                content_type=content_type,
            )

            # Generate URL
            return self._get_public_url(filename)

        except S3Error as e:
            raise StorageConnectionError(
                f"Failed to upload file '{filename}' to MinIO: {e}"
            )

    def _get_public_url(self, filename: str) -> str:
        """
        Generate public access URL for a file.

        Args:
            filename: Name of the file in the bucket

        Returns:
            Full HTTP URL to access the file
        """
        protocol = "https" if self._secure else "http"
        return f"{protocol}://{self._endpoint}/{self._bucket_name}/{filename}"

    @property
    def bucket_name(self) -> str:
        """Get the configured bucket name."""
        return self._bucket_name


# Module-level singleton instance
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """
    Get the singleton StorageService instance.

    Returns:
        StorageService instance

    Raises:
        StorageConnectionError: If connection to MinIO fails
    """
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
```

**Constraints**:
- MUST be thread-safe for read operations
- MUST validate MinIO connection at initialization
- MUST auto-create bucket with public read policy if not exists
- MUST raise `StorageConnectionError` for all MinIO failures
- MUST NOT modify client configuration after initialization

---

### REQ-STORAGE-002: FastAPI Dependency Injection

The system MUST provide a FastAPI dependency injection function in `app/core/deps.py`.

**Implementation**:

```python
# Add to existing app/core/deps.py

async def depends_storage(
    service: StorageService = Depends(get_storage_service),
) -> StorageService:
    """
    FastAPI dependency injection for StorageService.

    Usage in routes:
        @app.post("/upload")
        async def upload_diagnosis_image(
            file: UploadFile,
            storage: StorageService = Depends(depends_storage)
        ):
            url = storage.upload_image(file.file, file.filename)
            return {"url": url}

    Returns:
        StorageService: The singleton storage service instance
    """
    return service
```

---

### REQ-STORAGE-003: Error Handling

The system MUST define and use custom exceptions for storage operations.

**Exception Hierarchy**:

```python
class StorageConnectionError(Exception):
    """Raised when MinIO connection fails."""

    pass
```

**Error Messages**:
- Connection failure: `"Failed to connect to MinIO at {endpoint}: {error}"`
- Bucket creation failure: `"Failed to create or configure bucket '{bucket}': {error}"`
- Upload failure: `"Failed to upload file '{filename}' to MinIO: {error}"`

---

### REQ-STORAGE-004: Unit Testing

The system MUST include comprehensive unit tests in `tests/services/test_storage.py`.

**Test Coverage**:

#### Scenario: Service Initialization
**GIVEN** valid MinIO configuration
**WHEN** StorageService is initialized
**THEN** MinIO client is created
**AND** bucket exists or is created
**AND** bucket has public read policy

#### Scenario: Upload Image Successfully
**GIVEN** StorageService is initialized
**WHEN** calling `upload_image(file_data, "test.jpg")`
**THEN** file is uploaded to MinIO
**AND** returns URL like `http://localhost:9010/smart-agriculture/test.jpg`

#### Scenario: Upload with Custom Content Type
**GIVEN** StorageService is initialized
**WHEN** calling `upload_image(file_data, "test.png", "image/png")`
**THEN** file is uploaded with `Content-Type: image/png`
**AND** returns valid URL

#### Scenario: Connection Failure
**GIVEN** MinIO is not running
**WHEN** StorageService is initialized
**THEN** raises `StorageConnectionError`
**AND** error message contains endpoint address

#### Scenario: Singleton Pattern
**GIVEN** StorageService is initialized
**WHEN** creating multiple instances
**THEN** all instances are the same object
**AND** only one MinIO client is created

#### Scenario: Get Bucket Name
**GIVEN** StorageService is initialized
**WHEN** accessing `bucket_name` property
**THEN** returns configured bucket name

**Implementation**:

```python
import pytest
from minio.error import S3Error
from app.services.storage import (
    StorageService,
    StorageConnectionError,
    get_storage_service,
)
from unittest.mock import Mock, patch, MagicMock
import io


def test_storage_service_singleton():
    """Test that service is a singleton."""
    service1 = StorageService()
    service2 = StorageService()
    assert service1 is service2


def test_get_storage_service():
    """Test module-level factory function."""
    service = get_storage_service()
    assert isinstance(service, StorageService)


@patch("app.services.storage.Minio")
def test_upload_image_success(mock_minio):
    """Test successful image upload."""
    # Mock MinIO client
    mock_client = Mock()
    mock_minio.return_value = mock_client
    mock_client.bucket_exists.return_value = True

    # Create service with mocked client
    service = StorageService()
    service._client = mock_client

    # Mock file data
    file_data = io.BytesIO(b"fake image data")

    # Upload
    url = service.upload_image(file_data, "test.jpg")

    # Verify put_object was called
    mock_client.put_object.assert_called_once()

    # Verify URL format
    assert "test.jpg" in url
    assert service.bucket_name in url


@patch("app.services.storage.Minio")
def test_upload_image_with_custom_content_type(mock_minio):
    """Test upload with custom content type."""
    mock_client = Mock()
    mock_minio.return_value = mock_client
    mock_client.bucket_exists.return_value = True

    service = StorageService()
    service._client = mock_client

    file_data = io.BytesIO(b"fake png data")

    service.upload_image(file_data, "test.png", "image/png")

    # Verify content_type was passed
    call_args = mock_client.put_object.call_args
    assert call_args.kwargs["content_type"] == "image/png"


def test_bucket_name_property():
    """Test bucket_name property."""
    with patch("app.services.storage.Minio") as mock_minio:
        mock_client = Mock()
        mock_minio.return_value = mock_client
        mock_client.bucket_exists.return_value = True

        service = StorageService()
        assert service.bucket_name == "smart-agriculture"
```

**Note**: 由于集成测试需要真实的 MinIO 服务，单元测试应使用 `unittest.mock` 模拟 MinIO 客户端。

---

## MODIFIED Requirements

None (this is a new capability)

---

## DEPRECATED Requirements

None
