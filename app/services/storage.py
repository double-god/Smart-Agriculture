"""
StorageService for MinIO object storage operations.

This module provides a singleton service that encapsulates MinIO client
operations for uploading files and generating access URLs.
"""

from minio import Minio
from minio.error import S3Error
from app.core.config import get_settings
from typing import BinaryIO, Optional
import urllib3
import json


class StorageConnectionError(Exception):
    """
    Raised when MinIO connection fails.

    This exception is raised when:
    - MinIO server is unreachable
    - Authentication fails (invalid access key or secret key)
    - Bucket operations fail (creation, policy setting)

    Example:
        >>> try:
        ...     service = StorageService()
        ... except StorageConnectionError as e:
        ...     print(f"Storage error: {e}")
        Storage error: Failed to connect to MinIO at minio:9000: ...
    """

    pass


class StorageService:
    """
    Singleton service for MinIO object storage operations.

    This service manages MinIO client connections and provides
    simple methods for uploading files and generating access URLs.

    The service is a singleton to ensure only one MinIO client
    instance exists throughout the application lifecycle.

    Example:
        >>> service = get_storage_service()
        >>> with open("photo.jpg", "rb") as f:
        ...     url = service.upload_image(f, "diagnosis_123.jpg")
        ...     print(url)
        http://localhost:9010/smart-agriculture/diagnosis_123.jpg
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

    Example:
        >>> service = get_storage_service()
        >>> print(service.bucket_name)
        smart-agriculture
    """
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
