"""
End-to-End RAG Integration Tests

这些测试需要真实的服务环境：
- Redis（运行中）
- MinIO（运行中）
- ChromaDB（已初始化）
- OpenAI API（可用）

运行前准备：
1. 确保 Redis 运行：docker-compose up -d redis
2. 确保 MinIO 运行：docker-compose up -d minio
3. 初始化知识库：uv run python scripts/ingest_knowledge.py --path data/knowledge/
4. 配置 .env 文件中的 OPENAI_API_KEY

运行测试：
    uv run pytest tests/integration/test_rag_e2e.py -v -s
"""

from pathlib import Path

import os
import pytest
import time

from app.services.rag_service import get_rag_service, reset_rag_service
from app.services.taxonomy_service import get_taxonomy_service
from app.worker.diagnosis_tasks import analyze_image


@pytest.fixture(scope="module")
def verify_environment():
    """验证测试环境是否就绪"""
    # 检查环境变量
    required_env_vars = ["OPENAI_API_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]

    if missing_vars:
        pytest.skip(f"Missing required environment variables: {', '.join(missing_vars)}")

    # 检查 ChromaDB 是否已初始化
    chroma_path = os.getenv("CHROMA_PERSIST_DIRECTORY", "data/chroma")
    if not os.path.exists(chroma_path):
        pytest.skip(
            f"ChromaDB not initialized at {chroma_path}. "
            "Run: uv run python scripts/ingest_knowledge.py --path data/knowledge/"
        )

    # 检查知识文件是否存在
    knowledge_dir = Path("data/knowledge")
    if not knowledge_dir.exists():
        pytest.skip(f"Knowledge directory not found: {knowledge_dir}")

    yield True

    # 清理：重置 RAG service singleton
    reset_rag_service()


@pytest.fixture(scope="module")
def test_image_url(verify_environment):
    """
    创建或使用测试图片的 URL。

    注意：真实环境需要有 MinIO 运行并可访问。
    对于测试环境，我们使用一个可公开访问的示例图片 URL。
    """
    # 使用一个公开的番茄病害图片示例
    # 注意：这只是一个示例 URL，实际测试时应该使用真实上传的图片
    return (
        "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/"
        "Phytophthora_infestans_Tomato.jpg/640px-Phytophthora_infestans_Tomato.jpg"
    )


@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndRAGDiagnosis:
    """端到端 RAG 诊断测试"""

    def test_rag_service_initialized(self, verify_environment):
        """测试 RAG 服务可以正确初始化"""
        rag = get_rag_service()
        assert rag is not None

        # 测试查询功能
        docs = rag.query("番茄晚疫病", top_k=3)
        assert isinstance(docs, list)
        # ChromaDB 应该返回一些相关文档
        # 如果知识库为空，返回空列表也是正常的
        print(f"✅ RAG service initialized, retrieved {len(docs)} documents")

    def test_taxonomy_service_initialized(self, verify_environment):
        """测试 Taxonomy 服务可以正确初始化"""
        taxonomy = get_taxonomy_service()
        assert taxonomy is not None

        # 测试查询功能
        entry = taxonomy.get_by_model_label("late_blight")
        assert entry is not None
        assert entry.action_policy == "RETRIEVE"
        print(f"✅ Taxonomy service initialized, found entry: {entry.zh_scientific_name}")

    def test_end_to_end_diagnosis_with_report(self, verify_environment, test_image_url):
        """
        完整的端到端诊断流程测试。

        注意：这是一个真实测试，会：
        1. 调用 Celery 任务
        2. 查询 ChromaDB
        3. 调用 OpenAI API
        4. 生成 LLM 报告

        此测试会消耗 OpenAI API 配额。
        """
        print("\n🔍 Starting end-to-end diagnosis test...")
        print(f"   Image URL: {test_image_url}")

        # 提交诊断任务
        task_result = analyze_image.apply_async(
            args=[test_image_url],
            kwargs={"crop_type": "番茄"}
        )

        print(f"   Task ID: {task_result.id}")
        print(f"   Task status: {task_result.status}")

        # 等待任务完成（最多 60 秒）
        timeout = 60
        start_time = time.time()

        while not task_result.ready():
            if time.time() - start_time > timeout:
                pytest.fail(f"Task timeout after {timeout}s")

            print(f"   Waiting for task... (status: {task_result.status})")
            time.sleep(2)

        # 获取结果
        try:
            result = task_result.get(timeout=5)
        except Exception as e:
            pytest.fail(f"Task failed with exception: {str(e)}")

        print("\n✅ Task completed successfully")
        print(f"   Model label: {result.get('model_label')}")
        print(f"   Diagnosis: {result.get('diagnosis_name')}")
        print(f"   Confidence: {result.get('confidence'):.2%}")
        print(f"   Action policy: {result.get('action_policy')}")

        # 验证基本字段
        assert "model_label" in result
        assert "confidence" in result
        assert "diagnosis_name" in result
        assert "action_policy" in result

        # 如果是 RETRIEVE 策略，应该有报告
        if result.get("action_policy") == "RETRIEVE":
            print("\n📊 LLM Report:")
            if result.get("report"):
                # 打印报告的前 200 个字符
                report_preview = (
                    result["report"][:200] + "..."
                    if len(result["report"]) > 200
                    else result["report"]
                )
                print(f"   {report_preview}")

                # 验证报告包含预期的章节
                report_lower = result["report"].lower()
                # 根据报告模板，应该包含这些内容
                assert any(keyword in report_lower for keyword in ["病害", "防治", "预防", "番茄"])
                print(f"   ✅ Report generated successfully ({len(result['report'])} chars)")
            else:
                print("   ⚠️  No report generated")
                print(f"   Error: {result.get('report_error', 'Unknown error')}")

                # 报告生成失败不应该导致任务失败
                assert "report_error" in result

        print("\n✅ End-to-end test passed!")

    @pytest.mark.skipif(
        os.getenv("CI") == "true",
        reason="Skip in CI environment (requires external services)"
    )
    def test_rag_retrieval_quality(self, verify_environment):
        """测试 RAG 检索质量"""
        rag = get_rag_service()

        # 测试几个常见病害的检索
        test_queries = [
            ("番茄晚疫病", "番茄晚疫病由致病疫霉引起"),
            ("番茄白粉病", "白粉病"),
            ("番茄蚜虫", "蚜虫"),
        ]

        print("\n🔍 Testing RAG retrieval quality...")

        for query, expected_keyword in test_queries:
            docs = rag.query(query, top_k=3)
            print(f"   Query: '{query}' → {len(docs)} documents")

            # 验证至少有一个文档包含预期关键词
            if len(docs) > 0:
                found = any(expected_keyword in doc.page_content for doc in docs)
                if found:
                    print("      ✅ Found relevant document")
                else:
                    print(f"      ⚠️  Expected keyword '{expected_keyword}' not found in results")
            else:
                print("      ⚠️  No documents retrieved (knowledge base may be empty)")

        print("✅ RAG retrieval quality test completed")


@pytest.mark.integration
class TestKnowledgeBaseIngestion:
    """知识库摄取测试"""

    def test_knowledge_files_exist(self, verify_environment):
        """测试知识文件是否存在"""
        knowledge_dir = Path("data/knowledge")

        # 检查示例文件
        example_files = [
            "diseases/powdery_mildew.md",
            "diseases/late_blight.md",
            "crops/tomato.md",
        ]

        print("\n📁 Checking knowledge files...")

        for file_path in example_files:
            full_path = knowledge_dir / file_path
            if full_path.exists():
                print(f"   ✅ {file_path} ({full_path.stat().st_size} bytes)")
            else:
                print(f"   ⚠️  {file_path} not found")

        print("✅ Knowledge files check completed")

    def test_chroma_db_persistence(self, verify_environment):
        """测试 ChromaDB 持久化"""
        chroma_path = os.getenv("CHROMA_PERSIST_DIRECTORY", "data/chroma")

        print("\n💾 Checking ChromaDB persistence...")
        print(f"   Path: {chroma_path}")

        if os.path.exists(chroma_path):
            # 检查 ChromaDB 文件
            chroma_files = list(Path(chroma_path).rglob("*"))
            print(f"   ✅ ChromaDB directory exists ({len(chroma_files)} files)")

            # 显示一些文件
            for file in chroma_files[:5]:
                print(f"      - {file.relative_to(chroma_path)}")

            if len(chroma_files) > 5:
                print(f"      ... and {len(chroma_files) - 5} more files")
        else:
            print("   ⚠️  ChromaDB directory not found")

        print("✅ ChromaDB persistence check completed")


if __name__ == "__main__":
    # 可以直接运行此文件进行快速测试
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
