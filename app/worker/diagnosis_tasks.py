"""
Diagnosis tasks for Smart Agriculture system.

This module contains Celery tasks for image analysis and diagnosis.
"""

import asyncio
import logging
import random
import time
from typing import Optional

from app.core.ssrf_protection import (
    ImageDownloadError,
    SSRFValidationError,
    download_image_securely_async,
)
from app.services.rag_service import RAGServiceNotInitializedError, get_rag_service
from app.services.taxonomy_service import get_taxonomy_service
from app.worker.celery_app import celery_app
from app.worker.chains import (
    LLMError,
    ReportTimeoutError,
    generate_diagnosis_report,
    generate_diagnosis_report_async,
)

logger = logging.getLogger(__name__)


@celery_app.task(name="app.worker.diagnosis_tasks.analyze_image", bind=True)
def analyze_image(
    self,
    image_url: str,
    crop_type: Optional[str] = None,
    location: Optional[str] = None,
):
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
        # 1. 安全下载图片（异步 HTTP，包含 SSRF 防护和 DNS Rebinding 防护）
        logger.info(f"[Task {self.request.id}] Downloading image from: {image_url}")
        try:
            image_data = asyncio.run(
                download_image_securely_async(
                    image_url, max_size=10 * 1024 * 1024, timeout=30
                )
            )
            image_size = len(image_data)
            logger.info(
                f"[Task {self.request.id}] Image downloaded successfully, "
                f"size: {image_size} bytes"
            )
        except SSRFValidationError as e:
            # URL 验证失败（内网地址、不支持的协议等）
            raise RuntimeError(f"URL 验证失败: {str(e)}") from e
        except ImageDownloadError as e:
            # 图片下载失败（类型错误、大小超限等）
            raise RuntimeError(f"图片下载失败: {str(e)}") from e

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

        logger.info(
            f"[Task {self.request.id}] Mock inference result: "
            f"{mock_result['model_label']} (confidence: {mock_result['confidence']})"
        )

        # 3. 查询 TaxonomyService 获取详细信息
        taxonomy = get_taxonomy_service()
        try:
            taxonomy_entry = taxonomy.get_by_model_label(
                mock_result["model_label"]
            )
        except Exception as e:
            logger.warning(
                f"[Task {self.request.id}] Taxonomy entry not found for "
                f"{mock_result['model_label']}: {e}"
            )
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

        # 6. 生成 LLM 报告（如果需要）
        if taxonomy_entry and taxonomy_entry.action_policy == "RETRIEVE":
            logger.info(
                f"[Task {self.request.id}] Generating report for "
                f"{result['diagnosis_name']}..."
            )
            try:
                # 查询 RAG 服务获取相关知识（异步版本）
                rag = get_rag_service()
                query_text = f"{result.get('crop_type', '作物')} {result['diagnosis_name']}"
                contexts = asyncio.run(rag.query_async(query_text, top_k=3))

                logger.info(
                    f"[Task {self.request.id}] Retrieved {len(contexts)} "
                    f"documents from RAG (async)"
                )

                # 生成 LLM 报告 (使用异步版本提升并发性能)
                report = asyncio.run(
                    generate_diagnosis_report_async(
                        diagnosis_name=result["diagnosis_name"],
                        crop_type=result.get("crop_type", "未知"),
                        confidence=result["confidence"],
                        contexts=contexts,
                        timeout=30,
                    )
                )

                result["report"] = report
                result["report_error"] = None
                logger.info(
                    f"[Task {self.request.id}] Report generated successfully "
                    f"({len(report)} chars)"
                )

            except RAGServiceNotInitializedError as e:
                logger.warning(f"[Task {self.request.id}] RAG service not initialized: {str(e)}")
                result["report"] = None
                result["report_error"] = f"RAG service not initialized: {str(e)}"

            except (ReportTimeoutError, LLMError) as e:
                logger.error(f"[Task {self.request.id}] Report generation failed: {str(e)}")
                result["report"] = None
                result["report_error"] = str(e)

            except Exception as e:
                logger.error(
                    f"[Task {self.request.id}] Unexpected error during "
                    f"report generation: {str(e)}",
                    exc_info=True,
                )
                result["report"] = None
                result["report_error"] = f"Unexpected error: {str(e)}"
        else:
            # 不需要生成报告
            result["report"] = None
            result["report_error"] = None

        logger.info(
            f"[Task {self.request.id}] Diagnosis completed successfully: "
            f"{result['diagnosis_name']}"
        )

        return result

    except Exception as e:
        logger.error(f"[Task {self.request.id}] Diagnosis failed: {str(e)}", exc_info=True)
        # 重新抛出异常，Celery 会标记任务为 FAILURE
        raise
