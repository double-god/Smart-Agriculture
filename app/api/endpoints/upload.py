"""
Upload API endpoints for Smart Agriculture system.

This module provides image upload functionality using StorageService.
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from app.services.storage import StorageService, StorageConnectionError
from app.core import depends_storage
from app.models.diagnosis import UploadResponse
import uuid

router = APIRouter(prefix="/api/v1/upload", tags=["upload"])

# 允许的文件类型
ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/jpg", "image/png"]
# 最大文件大小 (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


@router.post("", response_model=UploadResponse)
async def upload_image(
    file: UploadFile = File(..., description="图片文件（支持 jpg, jpeg, png，最大 10MB）"),
    storage: StorageService = Depends(depends_storage),
) -> UploadResponse:
    """
    上传诊断图片到 MinIO 存储。

    Args:
        file: 上传的图片文件
        storage: StorageService 依赖注入

    Returns:
        包含图片 URL 和文件信息的字典

    Raises:
        HTTPException: 当文件类型不支持或上传失败时

    Example:
        POST /api/v1/upload
        Content-Type: multipart/form-data

        Response:
        {
            "url": "http://localhost:9010/smart-agriculture/a1b2c3d4-photo.jpg",
            "filename": "a1b2c3d4-photo.jpg",
            "original_filename": "photo.jpg",
            "content_type": "image/jpeg"
        }
    """
    # 验证文件类型
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}"
        )

    # 读取文件内容并验证大小
    file_content = await file.read()
    file_size = len(file_content)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {file_size} bytes. Maximum size: {MAX_FILE_SIZE} bytes"
        )

    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="Empty file"
        )

    # 生成唯一文件名
    file_extension = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
    unique_filename = f"{uuid.uuid4()}_{file.filename}"

    try:
        # 重置文件指针
        import io
        file.file = io.BytesIO(file_content)

        # 上传到 MinIO
        url = storage.upload_image(
            file.file,
            unique_filename,
            content_type=file.content_type
        )

        return UploadResponse(
            url=url,
            filename=unique_filename,
            original_filename=file.filename or "unknown",
            content_type=file.content_type
        )

    except StorageConnectionError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to upload image: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during upload: {str(e)}"
        )
