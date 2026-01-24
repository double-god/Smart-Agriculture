"""
Diagnosis data models for Smart Agriculture system.

This module contains Pydantic models for diagnosis workflow including
requests, responses, and results.
"""

from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class DiagnoseRequest(BaseModel):
    """诊断请求模型"""
    image_url: HttpUrl = Field(..., description="图片 URL")
    crop_type: Optional[str] = Field(None, description="作物类型（可选）")
    location: Optional[str] = Field(None, description="地理位置（可选）")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "image_url": "http://localhost:9010/smart-agriculture/abc123-photo.jpg",
                    "crop_type": "番茄",
                    "location": "大棚A区"
                }
            ]
        }
    }


class DiagnoseResponse(BaseModel):
    """诊断响应模型"""
    task_id: str = Field(..., description="Celery 任务 ID")
    status: str = Field(..., description="任务状态（PENDING, STARTED, SUCCESS, FAILURE）")
    message: str = Field(..., description="响应消息")


class DiagnosisResult(BaseModel):
    """诊断结果模型"""
    model_label: str = Field(..., description="CV 模型输出的标签")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度（0-1）")
    diagnosis_name: str = Field(..., description="中文名称")
    latin_name: Optional[str] = Field(None, description="拉丁学名")
    category: str = Field(..., description="分类（Pest, Disease, Status, Anomaly）")
    action_policy: str = Field(..., description="处理策略（PASS, RETRIEVE, HUMAN_REVIEW）")
    taxonomy_id: Optional[int] = Field(None, description="Taxonomy ID")
    inference_time_ms: int = Field(..., description="推理耗时（毫秒）")
    description: Optional[str] = Field(None, description="描述")
    risk_level: Optional[str] = Field(None, description="风险等级")
    crop_type: Optional[str] = Field(None, description="作物类型")
    location: Optional[str] = Field(None, description="地理位置")


class TaskStatus(BaseModel):
    """任务状态模型"""
    task_id: str = Field(..., description="Celery 任务 ID")
    status: str = Field(..., description="任务状态（PENDING, STARTED, SUCCESS, FAILURE, RETRY）")
    result: Optional[DiagnosisResult] = Field(None, description="诊断结果（仅在成功时）")
    error: Optional[str] = Field(None, description="错误信息（仅在失败时）")


class UploadResponse(BaseModel):
    """上传响应模型"""
    url: str = Field(..., description="图片访问 URL")
    filename: str = Field(..., description="存储的文件名（带 UUID 前缀）")
    original_filename: str = Field(..., description="原始文件名")
    content_type: str = Field(..., description="文件 MIME 类型")
