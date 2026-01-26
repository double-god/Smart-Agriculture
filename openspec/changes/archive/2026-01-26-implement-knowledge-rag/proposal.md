# Proposal: Implement Knowledge RAG and LLM Report Generation (implement-knowledge-rag)

**Change ID**: `implement-knowledge-rag`
**Status**: Proposed
**Created**: 2026-01-24
**Author**: Claude (Full-Stack Agent Architect)

---

## 1. Problem Statement

Smart-Agriculture 系统目前已经实现核心诊断工作流：
- ✅ **TaxonomyService** - 病虫害分类查询服务
- ✅ **StorageService** - MinIO 对象存储服务
- ✅ **Diagnosis Workflow** - 图片上传、诊断提交、结果轮询
- ✅ **Celery Worker** - 异步任务处理（analyze_image）

但是 `analyze_image` 任务目前**只返回结构化数据**（分类标签、置信度、拉丁名等），缺少：
- **知识库检索**：没有从农业知识库中检索相关上下文
- **自然语言报告**：没有生成可读的诊断报告
- **防治建议**：没有提供具体的防治措施和用药指导

这导致诊断结果对普通用户不够友好，无法提供实用的农业建议。

---

## 2. Proposed Solution

实现**知识库 RAG 检索 + LLM 报告生成**，在诊断流程中集成智能报告生成能力。

### 核心流程

```
┌──────────────────────────────────────────────────────────────┐
│  1. 知识库准备（一次性）                                       │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ scripts/ingest_knowledge.py                            │  │
│  │ - 读取本地 Markdown/PDF 文件                           │  │
│  │ - 切片（Chunking）                                      │  │
│  │ - 存入 ChromaDB 向量数据库                              │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  2. 诊断流程（每次诊断）                                       │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ app/worker/diagnosis_tasks.py::analyze_image          │  │
│  │                                                         │  │
│  │ 1. 下载图片                                              │  │
│  │ 2. Mock CV 推理 → model_label, confidence             │  │
│  │ 3. 查询 Taxonomy → category, action_policy           │  │
│  │                                                         │  │
│  │ 4. [NEW] 如果 action_policy == "RETRIEVE":           │  │
│  │    ┌──────────────────────────────────────┐           │  │
│  │    │ app/services/rag_service.py          │           │  │
│  │    │ - 向量检索（ChromaDB）                │           │  │
│  │    │ - 返回相关文档片段                    │           │  │
│  │    └──────────────────────────────────────┘           │  │
│  │         ↓                                               │  │
│  │    ┌──────────────────────────────────────┐           │  │
│  │    │ app/worker/chains.py                 │           │  │
│  │    │ - 构建 Prompt + Context              │           │  │
│  │    │ - 调用 LLM 生成报告                  │           │  │
│  │    │ - 返回自然语言报告                    │           │  │
│  │    └──────────────────────────────────────┘           │  │
│  │                                                         │  │
│  │ 5. 返回完整结果（结构化数据 + 报告）                    │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### 实施步骤

#### Task 1: 创建知识库摄取脚本 `scripts/ingest_knowledge.py`

**功能**：
- 扫描本地目录（如 `data/knowledge/`）中的 Markdown 和 PDF 文件
- 使用 LangChain TextSplitter 切片（chunk_size=1000, overlap=200）
- 使用 OpenAI Embeddings 或本地 Embeddings 生成向量
- 存入 ChromaDB 持久化存储

**接口**：
```bash
# 初始化知识库（一次性）
uv run python scripts/ingest_knowledge.py --path data/knowledge/

# 增量更新
uv run python scripts/ingest_knowledge.py --path data/knowledge/ --append
```

**输出**：
- ChromaDB 数据持久化到 `data/chroma/`
- 打印摄取统计：文件数、切片数、向量数

#### Task 2: 创建 RAG 服务 `app/services/rag_service.py`

**功能**：
- 封装 ChromaDB 客户端（Singleton）
- 提供 `query(query_text: str, top_k: int = 3)` 接口
- 返回相关文档片段及其元数据（来源、路径等）

**接口**：
```python
class RAGService:
    def query(self, query_text: str, top_k: int = 3) -> List[Document]:
        """向量检索相关文档

        Args:
            query_text: 查询文本（如 "番茄晚疫病 防治方法"）
            top_k: 返回最相关的 N 个文档片段

        Returns:
            List[Document]: 相关文档列表，包含 content 和 metadata
        """
```

#### Task 3: 修改诊断任务 `app/worker/diagnosis_tasks.py`

**变更**：
- 集成 `app/worker/chains.py`（创建新的报告生成链）
- 当 `TaxonomyService.action_policy == "RETRIEVE"` 时：
  1. 调用 `RAGService.query()` 检索相关知识
  2. 调用 `generate_diagnosis_report()` 生成报告
  3. 将报告添加到诊断结果中

**关键设计**：
```python
@celery_app.task(bind=True)
def analyze_image(self, image_url: str, crop_type: str = None, location: str = None):
    try:
        # 1-2. 下载图片 + Mock CV 推理
        # ...

        # 3. 查询 Taxonomy
        taxonomy = get_taxonomy_service()
        entry = taxonomy.get_by_model_label(mock_result["model_label"])

        result = {
            "model_label": mock_result["model_label"],
            "confidence": mock_result["confidence"],
            "diagnosis_name": entry.zh_scientific_name,
            # ... 其他结构化字段
            "report": None  # 默认无报告
        }

        # 4. [NEW] 生成报告（如果需要）
        if entry.action_policy == "RETRIEVE":
            try:
                rag = get_rag_service()
                contexts = rag.query(
                    query_text=f"{crop_type} {entry.zh_scientific_name} 防治",
                    top_k=3
                )

                from app.worker.chains import generate_diagnosis_report
                report = generate_diagnosis_report(
                    diagnosis_name=entry.zh_scientific_name,
                    crop_type=crop_type or "未知",
                    confidence=mock_result["confidence"],
                    contexts=[doc.page_content for doc in contexts]
                )

                result["report"] = report
            except Exception as e:
                # 关键：不要因为报告生成失败导致整个任务崩溃
                logger.error(f"[Task {self.request.id}] Failed to generate report: {str(e)}")
                result["report"] = None
                result["report_error"] = str(e)

        return result

    except Exception as e:
        logger.error(f"[Task {self.request.id}] Diagnosis failed: {str(e)}")
        raise
```

**异常处理**：
- RAG 检索失败 → 跳过报告生成，返回结构化数据
- LLM 调用失败 → 捕获异常，记录 `report_error`，不中断任务
- 超时 → 设置 LLM 调用超时（30 秒），超时则跳过

---

## 3. Architecture Decisions

### 3.1. 知识库格式
**决策**：使用 Markdown + PDF，支持结构化和非结构化文档。

**理由**：
- **Markdown**：易于编辑，支持 Git 版本控制
- **PDF**：农业专家常用格式，便于导入现有资料
- **统一切片**：LangChain 支持多种格式，统一处理

**示例结构**：
```
data/knowledge/
├── diseases/
│   ├── powdery_mildew.md
│   ├── late_blight.md
│   └── aphids.md
├── crops/
│   ├── tomato.md
│   └── cucumber.md
└── pesticides/
    └── common_pesticides.pdf
```

### 3.2. 向量数据库选择
**决策**：使用 ChromaDB。

**理由**：
- **轻量级**：无需额外服务，嵌入式存储
- **Python 原生**：与 LangChain 无缝集成
- **持久化**：支持磁盘存储，重启不丢失
- **性能**：支持元数据过滤和相似度排序

**权衡**：
- 不支持分布式（单机场景够用）
- 缓解措施：未来可升级到 Qdrant/Pinecone

### 3.3. Embedding 模型
**决策**：使用 OpenAI `text-embedding-3-small`（第一版）。

**理由**：
- **高质量**：OpenAI Embeddings 效果好
- **简单**：无需自己部署 Embedding 模型
- **成本**：`text-embedding-3-small` 价格低（$0.02/1M tokens）

**未来扩展**：
- 第二版：替换为本地模型（如 BGE-M3）降低成本
- 第三版：多语言 Embeddings 支持英文资料

### 3.4. LLM 选择
**决策**：使用 OpenAI GPT-4o-mini（第一版）。

**理由**：
- **速度快**：GPT-4o-mini 响应快（<3 秒）
- **成本低**：适合高频诊断场景
- **质量好**：生成的报告结构清晰、专业

**Prompt 模板**：
```
你是一位农业病虫害诊断专家。根据以下信息生成诊断报告：

【诊断结果】
作物：{crop_type}
病害：{diagnosis_name}
置信度：{confidence:.1%}

【相关知识】
{contexts}

请生成以下内容：
1. 病害描述（症状、成因）
2. 防治措施（生物防治、化学防治）
3. 推荐药剂（商品名、用量、注意事项）
4. 预防措施

格式要求：
- 使用清晰的分段和标题
- 语言专业但不晦涩
- 重点突出，便于阅读
```

### 3.5. 报告生成触发条件
**决策**：只有当 `Taxonomy.action_policy == "RETRIEVE"` 时才生成报告。

**理由**：
- **避免浪费**：健康样本无需生成报告
- **按需生成**：只有需要检索的分类才触发 RAG
- **性能优化**：减少不必要的 LLM 调用

**Taxonomy 示例**：
```json
{
  "model_label": "healthy",
  "action_policy": "IGNORE"  // 健康样本，不生成报告
}
{
  "model_label": "powdery_mildew",
  "action_policy": "RETRIEVE"  // 病害，生成报告
}
```

---

## 4. Impact Assessment

### 4.1. Affected Components
- **New Files Created**:
  - `scripts/ingest_knowledge.py` - 知识库摄取脚本
  - `app/services/rag_service.py` - RAG 服务封装
  - `app/worker/chains.py` - LLM 报告生成链
  - `tests/services/test_rag_service.py` - RAG 服务测试
  - `tests/worker/test_chains.py` - 报告生成链测试
  - `data/knowledge/` - 知识库目录（示例文档）
  - `data/chroma/` - ChromaDB 持久化存储

- **Modified Files**:
  - `app/worker/diagnosis_tasks.py` - 集成报告生成
  - `app/models/diagnosis.py` - 添加 `report` 和 `report_error` 字段
  - `pyproject.toml` - 添加依赖（chromadb, langchain, openai, pypdf）
  - `.env` - 添加 `OPENAI_API_KEY` 配置

### 4.2. Breaking Changes
- **None**（向后兼容，`report` 字段可选）

### 4.3. Migration Path
- 需要运行 `scripts/ingest_knowledge.py` 初始化知识库
- 需要配置 `OPENAI_API_KEY` 环境变量
- 需要安装新的 Python 依赖

---

## 5. Success Criteria

实现成功需满足以下条件：

1. [ ] `scripts/ingest_knowledge.py` 成功摄取 Markdown 和 PDF 文件
2. [ ] `RAGService.query()` 能返回相关文档片段
3. [ ] `generate_diagnosis_report()` 能生成结构化的诊断报告
4. [ ] `analyze_image` 任务在 `action_policy == "RETRIEVE"` 时生成报告
5. [ ] LLM 调用失败时不中断整个诊断任务
6. [ ] 生成的报告包含病害描述、防治措施、推荐药剂、预防措施
7. [ ] 端到端测试通过（摄取知识 → 诊断 → 生成报告）
8. [ ] 测试覆盖率 > 80%

---

## 6. Risks & Mitigations

| 风险 | 影响 | 缓解措施 |
|------|--------|----------|
| OpenAI API 调用失败/超时 | 高 | 设置 30 秒超时，失败时跳过报告生成，返回结构化数据 |
| Embedding 成本过高 | 中 | 使用 `text-embedding-3-small`，成本降低 90%；未来切换到本地模型 |
| 知识库质量不足 | 中 | 提供示例文档模板，逐步完善知识库内容 |
| ChromaDB 查询慢 | 低 | 使用持久化存储，预热缓存；未来可升级到 Qdrant |
| LLM 生成报告不稳定 | 中 | 使用结构化 Prompt，限制输出长度，添加验证逻辑 |
| 知识库更新不及时 | 低 | 提供增量摄取 `--append` 选项，支持定期更新 |

---

## 7. Open Questions

1. **Embedding 模型选择**：
   - 当前提案：OpenAI `text-embedding-3-small`
   - 备选方案：本地 BGE-M3 模型（降低成本，无需外网）

2. **知识库来源**：
   - 是否需要爬取农业网站数据？
   - 是否支持用户自定义知识库？

3. **报告缓存**：
   - 相同诊断是否复用报告？
   - 建议：第一版不缓存，第二版根据使用情况优化

4. **多语言支持**：
   - 当前知识库是否包含英文资料？
   - 建议：第一版仅中文，第二版支持多语言

---

## 8. Related Specifications

详细技术规范见 `openspec/changes/implement-knowledge-rag/specs/rag/spec.md`。

---

## 9. Implementation Phases

### Phase 1: 环境准备和依赖安装 (REQ-RAG-001)
- 添加依赖：chromadb, langchain, openai, pypdf, unstructured
- 配置 `OPENAI_API_KEY` 环境变量
- 创建 `data/knowledge/` 目录和示例文档

### Phase 2: 知识库摄取脚本 (REQ-RAG-002)
- 创建 `scripts/ingest_knowledge.py`
- 实现 Markdown 文件加载和切片
- 实现 PDF 文件加载和切片
- 集成 ChromaDB 向量存储
- 添加 CLI 参数（path, append, reset）

### Phase 3: RAG 服务封装 (REQ-RAG-003)
- 创建 `app/services/rag_service.py`
- 实现 Singleton ChromaDB 客户端
- 实现 `query()` 接口
- 添加元数据过滤支持

### Phase 4: LLM 报告生成链 (REQ-RAG-004)
- 创建 `app/worker/chains.py`
- 实现 `generate_diagnosis_report()` 函数
- 设计结构化 Prompt 模板
- 添加超时和异常处理

### Phase 5: 诊断任务集成 (REQ-RAG-005)
- 修改 `app/worker/diagnosis_tasks.py`
- 根据 `action_policy` 条件触发报告生成
- 添加异常处理（报告失败不中断任务）
- 更新 `DiagnosisResult` 模型

### Phase 6: 测试和验证 (REQ-RAG-006)
- 编写 RAG 服务单元测试
- 编写报告生成链单元测试
- 编写端到端测试
- 运行知识库摄取并验证
- 手动测试诊断流程和报告质量

### Phase 7: 文档和部署 (REQ-RAG-007)
- 创建知识库管理文档
- 更新诊断工作流文档
- 添加故障排查指南
- 准备部署检查清单
