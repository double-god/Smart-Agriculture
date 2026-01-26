"""
Diagnosis tasks for Smart Agriculture system.

This module contains Celery tasks for image analysis and diagnosis.
"""

import asyncio
import logging
import random
import time
from contextlib import contextmanager
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
    generate_diagnosis_report_async,
)

logger = logging.getLogger(__name__)


@contextmanager
def _timer(task_id: str, operation_name: str):
    """
    计时上下文管理器。

    Args:
        task_id: Celery 任务 ID
        operation_name: 操作名称（如 "image_download"）

    Yields:
        None

    Example:
        >>> with _timer(task_id, "image_download"):
        ...     image_data = download_image_securely_async(url)
    """
    start = time.time()
    try:
        yield
    finally:
        elapsed_ms = int((time.time() - start) * 1000)
        logger.info(f"[Task {task_id}] {operation_name} completed in {elapsed_ms}ms")


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
    task_id = self.request.id
    total_start = time.time()

    logger.info(f"[Task {task_id}] Starting diagnosis for image: {image_url}")

    try:
        # 1. 安全下载图片（异步 HTTP，包含 SSRF 防护和 DNS Rebinding 防护）
        logger.info(f"[Task {task_id}] Downloading image from: {image_url}")
        download_start = time.time()
        try:
            image_data = asyncio.run(
                download_image_securely_async(
                    image_url, max_size=10 * 1024 * 1024, timeout=30
                )
            )
            download_time_ms = int((time.time() - download_start) * 1000)
            image_size = len(image_data)
            logger.info(
                f"[Task {task_id}] Image downloaded successfully, "
                f"size: {image_size} bytes (took {download_time_ms}ms)"
            )
        except SSRFValidationError as e:
            # URL 验证失败（内网地址、不支持的协议等）
            raise RuntimeError(f"URL 验证失败: {str(e)}") from e
        except ImageDownloadError as e:
            # 图片下载失败（类型错误、大小超限等）
            raise RuntimeError(f"图片下载失败: {str(e)}") from e

        # 2. 模拟 CV 模型推理（Mock 数据）
        logger.info(f"[Task {task_id}] Running CV model inference...")
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
            f"[Task {task_id}] Mock inference result: "
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
                f"[Task {task_id}] Taxonomy entry not found for "
                f"{mock_result['model_label']}: {e}"
            )
            taxonomy_entry = None

        # 4. 构建诊断结果
        result = {
            "model_label": mock_result["model_label"],
            "confidence": mock_result["confidence"],
            "inference_time_ms": inference_time,
            "timings": {
                "image_download_ms": download_time_ms,
                "inference_ms": inference_time,
                "rag_query_ms": None,
                "llm_report_ms": None,
            },
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
                f"[Task {task_id}] Generating report for "
                f"{result['diagnosis_name']}..."
            )
            try:
                # 查询 RAG 服务获取相关知识（异步版本）
                rag = get_rag_service()
                query_text = f"{result.get('crop_type', '作物')} {result['diagnosis_name']}"

                # RAG 查询计时
                rag_start = time.time()
                contexts = asyncio.run(rag.query_async(query_text, top_k=3))
                rag_time = int((time.time() - rag_start) * 1000)
                result["timings"]["rag_query_ms"] = rag_time

                logger.info(
                    f"[Task {task_id}] Retrieved {len(contexts)} "
                    f"documents from RAG in {rag_time}ms"
                )

                # 生成 LLM 报告 (使用异步版本提升并发性能)
                llm_start = time.time()
                report = asyncio.run(
                    generate_diagnosis_report_async(
                        diagnosis_name=result["diagnosis_name"],
                        crop_type=result.get("crop_type", "未知"),
                        confidence=result["confidence"],
                        contexts=contexts,
                        timeout=30,
                    )
                )
                llm_time = int((time.time() - llm_start) * 1000)
                result["timings"]["llm_report_ms"] = llm_time

                result["report"] = report
                result["report_error"] = None
                logger.info(
                    f"[Task {task_id}] Report generated successfully "
                    f"({len(report)} chars) in {llm_time}ms"
                )

            except RAGServiceNotInitializedError as e:
                logger.warning(f"[Task {task_id}] RAG service not initialized: {str(e)}")
                result["report"] = None
                result["report_error"] = f"RAG service not initialized: {str(e)}"

            except (ReportTimeoutError, LLMError) as e:
                logger.error(f"[Task {task_id}] Report generation failed: {str(e)}")
                result["report"] = None
                result["report_error"] = str(e)

            except Exception as e:
                logger.error(
                    f"[Task {task_id}] Unexpected error during "
                    f"report generation: {str(e)}",
                    exc_info=True,
                )
                result["report"] = None
                result["report_error"] = f"Unexpected error: {str(e)}"
        else:
            # 不需要生成报告
            result["report"] = None
            result["report_error"] = None

        # 计算总耗时
        total_time = int((time.time() - total_start) * 1000)
        result["timings"]["total_ms"] = total_time

        logger.info(
            f"[Task {task_id}] Diagnosis completed: {result['diagnosis_name']} "
            f"(total: {total_time}ms)"
        )

        return result

    except Exception as e:
        total_time = int((time.time() - total_start) * 1000)
        logger.error(
            f"[Task {task_id}] Diagnosis failed after {total_time}ms: {str(e)}",
            exc_info=True,
        )
        # 重新抛出异常，Celery 会标记任务为 FAILURE
        raise
