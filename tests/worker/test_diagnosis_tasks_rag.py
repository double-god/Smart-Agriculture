"""
RAG + LLM 报告生成集成测试

Tests for RAG and LLM integration in diagnosis tasks.
"""

import pytest
from unittest.mock import Mock, patch
from app.worker.diagnosis_tasks import analyze_image
from langchain_core.documents import Document
from app.services.rag_service import RAGServiceNotInitializedError
from app.worker.chains import ReportTimeoutError, LLMError


def test_analyze_image_with_report():
    """测试成功生成报告（action_policy == RETRIEVE）"""
    with patch('app.worker.diagnosis_tasks.requests.get') as mock_get:
        # Mock HTTP 响应
        mock_response = Mock()
        mock_response.content = b"fake image data"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with patch('app.worker.diagnosis_tasks.get_taxonomy_service') as mock_get_taxonomy:
            # Mock TaxonomyService - 返回 RETRIEVE 策略
            mock_taxonomy = Mock()
            mock_entry = Mock()
            mock_entry.zh_scientific_name = "番茄晚疫病"
            mock_entry.latin_name = "Phytophthora infestans"
            mock_entry.category = "Disease"
            mock_entry.action_policy = "RETRIEVE"
            mock_entry.id = 1
            mock_entry.description = "致病疫霉引起的病害"
            mock_entry.risk_level = "high"
            mock_taxonomy.get_by_model_label.return_value = mock_entry
            mock_get_taxonomy.return_value = mock_taxonomy

            with patch('app.worker.diagnosis_tasks.get_rag_service') as mock_get_rag:
                # Mock RAG 服务
                mock_rag = Mock()
                mock_docs = [
                    Document(
                        page_content="番茄晚疫病由致病疫霉引起，主要危害叶片和果实。",
                        metadata={"source": "data/knowledge/diseases/late_blight.md"}
                    ),
                    Document(
                        page_content="推荐使用68.75%银法利悬浮剂，用量60-75 ml/亩。",
                        metadata={"source": "data/knowledge/diseases/late_blight.md"}
                    ),
                ]
                mock_rag.query.return_value = mock_docs
                mock_get_rag.return_value = mock_rag

                with patch('app.worker.diagnosis_tasks.generate_diagnosis_report') as mock_generate:
                    # Mock LLM 报告生成
                    mock_report = """# 番茄晚疫病诊断报告

## 病害描述
番茄晚疫病由致病疫霉（Phytophthora infestans）引起...

## 防治措施
1. 农业防治：选用抗病品种
2. 化学防治：68.75%银法利悬浮剂，60-75 ml/亩

## 预防措施
加强通风，降低湿度...
"""
                    mock_generate.return_value = mock_report

                    # 执行任务（使用 Celery apply 方法）
                    result = analyze_image.apply(
                        args=["http://example.com/test.jpg"],
                        kwargs={"crop_type": "番茄"}
                    ).result

                    # 验证报告生成
                    assert result["report"] is not None
                    assert result["report"] == mock_report
                    assert result["report_error"] is None

                    # 验证 RAG 和 LLM 被调用
                    mock_rag.query.assert_called_once()
                    mock_generate.assert_called_once()


def test_analyze_image_skip_report_healthy():
    """测试健康样本不生成报告（action_policy == PASS）"""
    with patch('app.worker.diagnosis_tasks.requests.get') as mock_get:
        # Mock HTTP 响应
        mock_response = Mock()
        mock_response.content = b"fake image data"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with patch('app.worker.diagnosis_tasks.get_taxonomy_service') as mock_get_taxonomy:
            # Mock TaxonomyService - 返回 PASS 策略（健康）
            mock_taxonomy = Mock()
            mock_entry = Mock()
            mock_entry.zh_scientific_name = "健康"
            mock_entry.latin_name = "Healthy"
            mock_entry.category = "Status"
            mock_entry.action_policy = "PASS"  # 不生成报告
            mock_entry.id = 1
            mock_entry.description = "植株健康"
            mock_entry.risk_level = "none"
            mock_taxonomy.get_by_model_label.return_value = mock_entry
            mock_get_taxonomy.return_value = mock_taxonomy

            with patch('app.worker.diagnosis_tasks.get_rag_service') as mock_get_rag:
                # Mock RAG 服务
                mock_rag = Mock()
                mock_get_rag.return_value = mock_rag

                # 执行任务
                result = analyze_image.apply(
                    args=["http://example.com/test.jpg"]
                ).result

                # 验证不生成报告
                assert result["report"] is None
                assert result["report_error"] is None

                # 验证 RAG 和 LLM 未被调用
                mock_rag.query.assert_not_called()


def test_analyze_image_rag_failure():
    """测试 RAG 服务失败处理"""
    with patch('app.worker.diagnosis_tasks.requests.get') as mock_get:
        # Mock HTTP 响应
        mock_response = Mock()
        mock_response.content = b"fake image data"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with patch('app.worker.diagnosis_tasks.get_taxonomy_service') as mock_get_taxonomy:
            # Mock TaxonomyService - 返回 RETRIEVE 策略
            mock_taxonomy = Mock()
            mock_entry = Mock()
            mock_entry.zh_scientific_name = "番茄晚疫病"
            mock_entry.latin_name = "Phytophthora infestans"
            mock_entry.category = "Disease"
            mock_entry.action_policy = "RETRIEVE"
            mock_entry.id = 1
            mock_entry.description = "致病疫霉引起的病害"
            mock_entry.risk_level = "high"
            mock_taxonomy.get_by_model_label.return_value = mock_entry
            mock_get_taxonomy.return_value = mock_taxonomy

            with patch('app.worker.diagnosis_tasks.get_rag_service') as mock_get_rag:
                # Mock RAG 服务抛出异常
                mock_rag = Mock()
                mock_rag.query.side_effect = RAGServiceNotInitializedError("ChromaDB not initialized")
                mock_get_rag.return_value = mock_rag

                # 执行任务
                result = analyze_image.apply(
                    args=["http://example.com/test.jpg"],
                    kwargs={"crop_type": "番茄"}
                ).result

                # 验证报告为空，但有错误信息
                assert result["report"] is None
                assert result["report_error"] is not None
                assert "RAG service not initialized" in result["report_error"]

                # 验证任务未失败（其他结果仍然有效）
                assert result["diagnosis_name"] == "番茄晚疫病"
                assert result["taxonomy_id"] == 1


def test_analyze_image_llm_timeout():
    """测试 LLM 超时处理"""
    with patch('app.worker.diagnosis_tasks.requests.get') as mock_get:
        # Mock HTTP 响应
        mock_response = Mock()
        mock_response.content = b"fake image data"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with patch('app.worker.diagnosis_tasks.get_taxonomy_service') as mock_get_taxonomy:
            # Mock TaxonomyService - 返回 RETRIEVE 策略
            mock_taxonomy = Mock()
            mock_entry = Mock()
            mock_entry.zh_scientific_name = "番茄晚疫病"
            mock_entry.latin_name = "Phytophthora infestans"
            mock_entry.category = "Disease"
            mock_entry.action_policy = "RETRIEVE"
            mock_entry.id = 1
            mock_entry.description = "致病疫霉引起的病害"
            mock_entry.risk_level = "high"
            mock_taxonomy.get_by_model_label.return_value = mock_entry
            mock_get_taxonomy.return_value = mock_taxonomy

            with patch('app.worker.diagnosis_tasks.get_rag_service') as mock_get_rag:
                # Mock RAG 服务
                mock_rag = Mock()
                mock_docs = [
                    Document(page_content="测试文档", metadata={"source": "test.md"})
                ]
                mock_rag.query.return_value = mock_docs
                mock_get_rag.return_value = mock_rag

                with patch('app.worker.diagnosis_tasks.generate_diagnosis_report') as mock_generate:
                    # Mock LLM 超时
                    mock_generate.side_effect = ReportTimeoutError("LLM call timed out")

                    # 执行任务
                    result = analyze_image.apply(
                        args=["http://example.com/test.jpg"],
                        kwargs={"crop_type": "番茄"}
                    ).result

                    # 验证报告为空，但有错误信息
                    assert result["report"] is None
                    assert result["report_error"] is not None
                    assert "LLM call timed out" in result["report_error"] or "timed out" in result["report_error"].lower()

                    # 验证任务未失败（其他结果仍然有效）
                    assert result["diagnosis_name"] == "番茄晚疫病"
                    assert result["taxonomy_id"] == 1


def test_analyze_image_llm_api_error():
    """测试 LLM API 错误处理"""
    with patch('app.worker.diagnosis_tasks.requests.get') as mock_get:
        # Mock HTTP 响应
        mock_response = Mock()
        mock_response.content = b"fake image data"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with patch('app.worker.diagnosis_tasks.get_taxonomy_service') as mock_get_taxonomy:
            # Mock TaxonomyService - 返回 RETRIEVE 策略
            mock_taxonomy = Mock()
            mock_entry = Mock()
            mock_entry.zh_scientific_name = "番茄晚疫病"
            mock_entry.latin_name = "Phytophthora infestans"
            mock_entry.category = "Disease"
            mock_entry.action_policy = "RETRIEVE"
            mock_entry.id = 1
            mock_entry.description = "致病疫霉引起的病害"
            mock_entry.risk_level = "high"
            mock_taxonomy.get_by_model_label.return_value = mock_entry
            mock_get_taxonomy.return_value = mock_taxonomy

            with patch('app.worker.diagnosis_tasks.get_rag_service') as mock_get_rag:
                # Mock RAG 服务
                mock_rag = Mock()
                mock_docs = [
                    Document(page_content="测试文档", metadata={"source": "test.md"})
                ]
                mock_rag.query.return_value = mock_docs
                mock_get_rag.return_value = mock_rag

                with patch('app.worker.diagnosis_tasks.generate_diagnosis_report') as mock_generate:
                    # Mock LLM API 错误
                    mock_generate.side_effect = LLMError("OpenAI API rate limit exceeded")

                    # 执行任务
                    result = analyze_image.apply(
                        args=["http://example.com/test.jpg"],
                        kwargs={"crop_type": "番茄"}
                    ).result

                    # 验证报告为空，但有错误信息
                    assert result["report"] is None
                    assert result["report_error"] is not None
                    assert "rate limit" in result["report_error"].lower()

                    # 验证任务未失败
                    assert result["diagnosis_name"] == "番茄晚疫病"
                    assert result["taxonomy_id"] == 1
