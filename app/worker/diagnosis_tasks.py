"""
Diagnosis tasks for Smart Agriculture system.

This module contains Celery tasks for image analysis and diagnosis.
"""

from app.worker.celery_app import celery_app
from app.services.taxonomy_service import TaxonomyService, get_taxonomy_service
import requests
import logging
import time
import random

logger = logging.getLogger(__name__)


@celery_app.task(name="app.worker.diagnosis_tasks.analyze_image", bind=True)
def analyze_image(self, image_url: str, crop_type: str = None, location: str = None):
    """
    分析图片并返回诊断结果（Mock 版本）。

    Args:
        self: Celery task instance (for bind=True)
        image_url: 图片 URL
        crop_type: 可选的作物类型
        location: 可选的地理位置

    Returns:
        诊断结果字典

    Mock 数据格式:
        {
            "model_label": "powdery_mildew",
            "confidence": 0.92,
            "diagnosis_name": "白粉病",
            "category": "Disease",
            "action_policy": "RETRIEVE",
            "inference_time_ms": 150,
            "taxonomy_id": 2
        }
    """
    logger.info(f"[Task {self.request.id}] Starting diagnosis for image: {image_url}")

    try:
        # 1. 下载图片（验证 URL 可访问性）
        logger.info(f"[Task {self.request.id}] Downloading image from: {image_url}")
        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            image_size = len(response.content)
            logger.info(f"[Task {self.request.id}] Image downloaded successfully, size: {image_size} bytes")
        except requests.exceptions.Timeout:
            raise RuntimeError(f"Timeout while downloading image from {image_url}")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to download image: {str(e)}")

        # 2. 模拟 CV 模型推理（Mock 数据）
        logger.info(f"[Task {self.request.id}] Running CV model inference...")
        start_time = time.time()

        # Mock: 随机选择一个分类结果
        mock_results = [
            {
                "model_label": "healthy",
                "confidence": 0.95,
            },
            {
                "model_label": "powdery_mildew",
                "confidence": 0.87,
            },
            {
                "model_label": "aphid_complex",
                "confidence": 0.92,
            },
            {
                "model_label": "spider_mite",
                "confidence": 0.78,
            },
            {
                "model_label": "late_blight",
                "confidence": 0.85,
            },
        ]

        mock_result = random.choice(mock_results)
        inference_time = int((time.time() - start_time) * 1000)

        logger.info(f"[Task {self.request.id}] Mock inference result: {mock_result['model_label']} (confidence: {mock_result['confidence']})")

        # 3. 查询 TaxonomyService 获取详细信息
        taxonomy = get_taxonomy_service()
        try:
            taxonomy_entry = taxonomy.get_by_model_label(mock_result["model_label"])
        except Exception as e:
            logger.warning(f"[Task {self.request.id}] Taxonomy entry not found for {mock_result['model_label']}: {e}")
            taxonomy_entry = None

        # 4. 构建诊断结果
        result = {
            "model_label": mock_result["model_label"],
            "confidence": mock_result["confidence"],
            "inference_time_ms": inference_time,
        }

        if taxonomy_entry:
            result.update({
                "diagnosis_name": taxonomy_entry.zh_scientific_name,
                "latin_name": taxonomy_entry.latin_name,
                "category": taxonomy_entry.category,
                "action_policy": taxonomy_entry.action_policy,
                "taxonomy_id": taxonomy_entry.id,
                "description": taxonomy_entry.description,
                "risk_level": taxonomy_entry.risk_level,
            })
        else:
            result.update({
                "diagnosis_name": "未知",
                "latin_name": "Unknown",
                "category": "Unknown",
                "action_policy": "HUMAN_REVIEW",
                "taxonomy_id": None,
            })

        # 5. 添加可选参数
        if crop_type:
            result["crop_type"] = crop_type
        if location:
            result["location"] = location

        logger.info(f"[Task {self.request.id}] Diagnosis completed successfully: {result['diagnosis_name']}")

        return result

    except Exception as e:
        logger.error(f"[Task {self.request.id}] Diagnosis failed: {str(e)}", exc_info=True)
        # 重新抛出异常，Celery 会标记任务为 FAILURE
        raise
