"""
Unit tests for StorageService.

Tests cover singleton pattern, file upload, bucket management, and error handling.
"""

import pytest
from minio.error import S3Error
from app.services.storage import (
    StorageService,
    StorageConnectionError,
    get_storage_service,
)
from unittest.mock import Mock, patch, MagicMock
import io


@patch("app.services.storage.Minio")
def test_storage_service_singleton(mock_minio):
    """Test that service is a singleton."""
    mock_client = Mock()
    mock_minio.return_value = mock_client
    mock_client.bucket_exists.return_value = True

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


@patch("app.services.storage.Minio")
def test_bucket_name_property(mock_minio):
    """Test bucket_name property."""
    with patch("app.services.storage.Minio") as mock_minio:
        mock_client = Mock()
        mock_minio.return_value = mock_client
        mock_client.bucket_exists.return_value = True

        service = StorageService()
        assert service.bucket_name == "smart-agriculture"


@patch("app.services.storage.Minio")
def test_get_public_url_http(mock_minio):
    """Test URL generation for HTTP (non-secure)."""
    mock_client = Mock()
    mock_minio.return_value = mock_client
    mock_client.bucket_exists.return_value = True

    service = StorageService()
    service._client = mock_client

    url = service._get_public_url("test.jpg")
    assert url.startswith("http://")
    assert "test.jpg" in url


@patch("app.services.storage.Minio")
def test_upload_image_failure_raises_storage_error(mock_minio):
    """Test that upload failure raises StorageConnectionError."""
    mock_client = Mock()
    mock_minio.return_value = mock_client
    mock_client.bucket_exists.return_value = True

    # Create S3Error with proper constructor
    mock_response = Mock()
    mock_response.status = 400
    mock_response.headers = {}

    # Make put_object raise S3Error
    mock_client.put_object.side_effect = S3Error(
        "Failed to upload",
        mock_response,
        "GET",
        "bucket",
        "object",
        "host_id"
    )

    service = StorageService()
    service._client = mock_client

    file_data = io.BytesIO(b"fake image data")

    with pytest.raises(StorageConnectionError) as exc_info:
        service.upload_image(file_data, "test.jpg")

    assert "Failed to upload file 'test.jpg' to MinIO" in str(exc_info.value)
