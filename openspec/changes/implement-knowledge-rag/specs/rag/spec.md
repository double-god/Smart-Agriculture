# Specification: Knowledge RAG and LLM Report Generation

**Capability**: RAG (Retrieval-Augmented Generation)
**Version**: 1.0
**Status: Proposed

---

## ADDED Requirements

### REQ-RAG-001: 环境准备和依赖管理

系统必须安装并配置以下依赖和组件：

**Dependencies**:
- `chromadb>=0.4.0` - 向量数据库
- `langchain>=0.1.0` - LLM 应用框架
- `langchain-openai>=0.0.5` - OpenAI 集成
- `openai>=1.0.0` - OpenAI API 客户端
- `pypdf>=3.0.0` - PDF 解析
- `unstructured>=0.10.0` - 非结构化文档解析
- `tiktoken>=0.5.0` - Token 计数

**Environment Variables**:
- `OPENAI_API_KEY` - OpenAI API 密钥（必需）
- `CHROMA_PERSIST_DIRECTORY` - ChromaDB 持久化路径（默认：`data/chroma`）

**Directories**:
- `data/knowledge/` - 知识库文档目录
- `data/chroma/` - ChromaDB 持久化存储

#### Scenario: 安装依赖并配置环境

**GIVEN** 系统已安装 uv 包管理器
**WHEN** 运行 `uv add chromadb langchain langchain-openai openai pypdf unstructured tiktoken`
**THEN** 所有包成功安装且无版本冲突

#### Scenario: 配置 OpenAI API 密钥

**GIVEN** 项目根目录存在 `.env` 文件
**WHEN** 在 `.env` 中添加 `OPENAI_API_KEY=sk-...`
**THEN** 应用启动时能正确读取该环境变量

---

### REQ-RAG-002: 知识库摄取脚本

系统必须提供知识库摄取脚本，支持 Markdown 和 PDF 文件的向量化存储。

**Interface**:
```bash
uv run python scripts/ingest_knowledge.py [OPTIONS]

Options:
  --path PATH       知识库目录路径（默认：data/knowledge/）
  --append          增量模式，保留现有数据（默认：False）
  --reset           重置数据库，删除所有现有数据（默认：False）
  --chunk-size INT  切片大小（默认：1000）
  --overlap INT     切片重叠（默认：200）
```

**Behavior**:
1. 扫描指定目录中的所有 `.md` 和 `.pdf` 文件
2. 使用 LangChain TextSplitter 切片文档
3. 使用 OpenAI Embeddings 生成向量
4. 存入 ChromaDB 持久化存储
5. 打印摄取统计信息（文件数、切片数、用时）

#### Scenario: 首次摄取知识库

**GIVEN** `data/knowledge/` 目录包含 3 个 Markdown 文件
**WHEN** 运行 `uv run python scripts/ingest_knowledge.py --path data/knowledge/`
**THEN** 脚本成功完成并输出：
  - ✅ Processed 3 files
  - ✅ Created 45 chunks
  - ✅ Stored in ChromaDB: data/chroma/
  - ✅ Time elapsed: 12.3s

#### Scenario: 增量更新知识库

**GIVEN** ChromaDB 已有 10 个文档的向量
**WHEN** 运行 `uv run python scripts/ingest_knowledge.py --path data/knowledge/ --append`
**THEN** 新文档被添加到现有数据库，原有数据保留

#### Scenario: 重置知识库

**GIVEN** ChromaDB 已有 10 个文档的向量
**WHEN** 运行 `uv run python scripts/ingest_knowledge.py --path data/knowledge/ --reset`
**THEN** 数据库被清空，重新摄取所有文档

#### Scenario: 处理不支持的文件格式

**GIVEN** `data/knowledge/` 目录包含 `.txt`, `.docx` 文件
**WHEN** 运行摄取脚本
**THEN** 跳过不支持的文件并记录警告

#### Scenario: 处理空目录

**GIVEN** `data/knowledge/` 目录为空
**WHEN** 运行摄取脚本
**THEN** 输出 ⚠️ No documents found in data/knowledge/ 并退出

---

### REQ-RAG-003: RAG 服务封装

系统必须提供 RAG 服务，封装向量检索逻辑。

**Interface**:
```python
class RAGService:
    """RAG 向量检索服务（Singleton）"""

    def query(
        self,
        query_text: str,
        top_k: int = 3,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """向量检索相关文档

        Args:
            query_text: 查询文本（如 "番茄晚疫病 防治方法"）
            top_k: 返回最相关的 N 个文档片段
            filter_metadata: 元数据过滤条件（如 {"category": "disease"}）

        Returns:
            List[Document]: 相关文档列表，每个包含：
                - page_content: str - 文档内容
                - metadata: Dict - 元数据（source, page, category 等）
        """
```

**Singleton Pattern**:
- 全局只有一个 RAGService 实例
- 使用 `get_rag_service()` 函数获取实例

#### Scenario: 成功检索相关文档

**GIVEN** ChromaDB 存储了番茄病害相关文档
**WHEN** 调用 `rag.query("番茄晚疫病 防治方法", top_k=3)`
**THEN** 返回 3 个最相关的文档片段，按相似度排序

#### Scenario: 元数据过滤

**GIVEN** ChromaDB 存储了病害和作物两类文档
**WHEN** 调用 `rag.query("番茄", filter_metadata={"category": "disease"})`
**THEN** 只返回病害类别的文档

#### Scenario: 空查询结果

**GIVEN** ChromaDB 中没有与 "量子力学" 相关的文档
**WHEN** 调用 `rag.query("量子力学")`
**THEN** 返回空列表（不抛出异常）

#### Scenario: 数据库未初始化

**GIVEN** ChromaDB 持久化目录不存在或为空
**WHEN** 调用 `get_rag_service()`
**THEN** 抛出 `RAGServiceNotInitializedError` 异常

---

### REQ-RAG-004: LLM 报告生成链

系统必须提供 LLM 报告生成链，根据诊断结果和检索上下文生成自然语言报告。

**Interface**:
```python
def generate_diagnosis_report(
    diagnosis_name: str,
    crop_type: str,
    confidence: float,
    contexts: List[str],
    llm: Optional[BaseLLM] = None,
    timeout: int = 30
) -> str:
    """生成诊断报告

    Args:
        diagnosis_name: 诊断名称（如 "晚疫病"）
        crop_type: 作物类型（如 "番茄"）
        confidence: 置信度（0.0-1.0）
        contexts: RAG 检索到的相关文档片段
        llm: LLM 实例（默认使用 OpenAI GPT-4o-mini）
        timeout: 超时时间（秒）

    Returns:
        str: 生成的诊断报告（Markdown 格式）

    Raises:
        TimeoutError: LLM 调用超时
        LLMError: LLM 调用失败
    """
```

**Report Structure**:
```markdown
# 番茄晚疫病诊断报告

## 病害描述
晚疫病是由致病疫霉引起的... [症状、成因]

## 防治措施

### 生物防治
- 使用枯草芽孢杆菌制剂...
- 释放天敌昆虫...

### 化学防治
- 发病初期使用 68.75% 银法利悬浮剂...
- 每 7-10 天喷施一次...

## 推荐药剂
1. **68.75% 银法利悬浮剂**
   - 用量：60-75 ml/亩
   - 稀释 1500 倍液喷雾
   - 注意：安全间隔期 3 天

2. **72% 霜脲·锰锌可湿性粉剂**
   - 用量：100-133 g/亩
   - 注意：避免高温时段施药

## 预防措施
- 选用抗病品种...
- 合理轮作...
- 控制种植密度...
```

#### Scenario: 成功生成报告

**GIVEN** 诊断结果为 "晚疫病"，置信度 0.92，检索到 3 个相关文档
**WHEN** 调用 `generate_diagnosis_report("晚疫病", "番茄", 0.92, contexts)`
**THEN** 返回完整的 Markdown 报告，包含所有必需章节

#### Scenario: LLM 调用超时

**GIVEN** OpenAI API 响应缓慢
**WHEN** 调用 `generate_diagnosis_report(..., timeout=30)`
**THEN** 30 秒后抛出 `TimeoutError`

#### Scenario: 上下文为空

**GIVEN** RAG 检索未找到相关文档，`contexts = []`
**WHEN** 调用 `generate_diagnosis_report("晚疫病", "番茄", 0.92, [])`
**THEN** LLM 基于通用知识生成报告，但提示 "未找到相关资料"

#### Scenario: 置信度很低

**GIVEN** 诊断置信度为 0.55
**WHEN** 生成报告
**THEN** 报告中包含警告："⚠️ 置信度较低 (55%)，建议重新拍照诊断"

---

### REQ-RAG-005: 诊断任务集成

系统必须在诊断任务中集成报告生成，当 `action_policy == "RETRIEVE"` 时触发 RAG 检索和 LLM 生成。

**Behavior**:
1. 完成 CV 推理和 Taxonomy 查询后
2. 检查 `taxonomy_entry.action_policy`
3. 如果为 `"RETRIEVE"`：
   - 调用 `RAGService.query()` 检索相关知识
   - 调用 `generate_diagnosis_report()` 生成报告
   - 将报告添加到诊断结果
4. 如果为 `"IGNORE"`：跳过报告生成
5. 如果报告生成失败：记录错误但不中断任务

**Data Model Changes**:
```python
class DiagnosisResult(BaseModel):
    # ... 现有字段

    report: Optional[str] = Field(None, description="LLM 生成的诊断报告（Markdown）")
    report_error: Optional[str] = Field(None, description="报告生成错误信息")
```

#### Scenario: 病害诊断生成报告

**GIVEN** CV 推理结果为 "powdery_mildew"，Taxonomy 中 `action_policy == "RETRIEVE"`
**WHEN** 执行 `analyze_image` 任务
**THEN** 任务成功返回，`result["report"]` 包含完整的诊断报告

#### Scenario: 健康样本不生成报告

**GIVEN** CV 推理结果为 "healthy"，Taxonomy 中 `action_policy == "IGNORE"`
**WHEN** 执行 `analyze_image` 任务
**THEN** 任务成功返回，`result["report"]` 为 `None`

#### Scenario: RAG 检索失败

**GIVEN** ChromaDB 服务未启动
**WHEN** 执行 `analyze_image` 任务且需要生成报告
**THEN** 任务成功返回，`result["report"]` 为 `None`，`result["report_error"]` 包含错误信息

#### Scenario: LLM 调用失败

**GIVEN** OpenAI API 密钥无效
**WHEN** 执行 `analyze_image` 任务且需要生成报告
**THEN** 任务成功返回，`result["report"]` 为 `None`，`result["report_error"]` 包含 "LLM call failed"

#### Scenario: 报告生成超时

**GIVEN** OpenAI API 响应超时
**WHEN** 执行 `analyze_image` 任务且需要生成报告
**THEN** 任务成功返回，`result["report"]` 为 `None`，`result["report_error"]` 包含 "Timeout after 30s"

---

### REQ-RAG-006: 测试覆盖

系统必须包含完整的单元测试和集成测试。

**Test Coverage Requirements**:
- RAG 服务测试：`tests/services/test_rag_service.py`
- 报告生成链测试：`tests/worker/test_chains.py`
- 诊断任务集成测试：`tests/worker/test_diagnosis_tasks.py`（更新）
- 端到端测试：`tests/integration/test_rag_e2e.py`

**Minimum Coverage**: 80%

#### Scenario: RAG 服务单元测试

**GIVEN** ChromaDB 已初始化并包含测试数据
**WHEN** 运行 `uv run pytest tests/services/test_rag_service.py -v`
**THEN** 所有测试通过，覆盖以下场景：
  - ✅ 成功检索文档
  - ✅ 元数据过滤
  - ✅ 空查询结果
  - ✅ 数据库未初始化
  - ✅ 并发查询

#### Scenario: 报告生成链单元测试

**GIVEN** OpenAI API 可用（或 Mock）
**WHEN** 运行 `uv run pytest tests/worker/test_chains.py -v`
**THEN** 所有测试通过，覆盖以下场景：
  - ✅ 成功生成报告
  - ✅ LLM 调用超时
  - ✅ 上下文为空
  - ✅ 置信度低
  - ✅ LLM API 错误

#### Scenario: 端到端测试

**GIVEN** 所有服务运行（FastAPI, Celery Worker, ChromaDB）
**WHEN** 运行完整测试流程：
  1. 摄取知识库
  2. 上传图片
  3. 提交诊断
  4. 轮询结果
**THEN** 最终结果包含完整的诊断报告

---

### REQ-RAG-007: 文档和部署

系统必须提供完整的使用文档和部署指南。

**Documentation Requirements**:
1. `docs/knowledge_rag.md` - RAG 系统使用指南
   - 知识库管理
   - 摄取脚本使用
   - 故障排查

2. `docs/report_generation.md` - 报告生成说明
   - Prompt 模板
   - 报告结构
   - 自定义配置

3. 更新 `docs/diagnosis_workflow.md` - 添加报告生成章节

**Deployment Checklist**:
- [ ] 配置 `OPENAI_API_KEY`
- [ ] 运行 `scripts/ingest_knowledge.py` 初始化知识库
- [ ] 验证 ChromaDB 数据目录存在
- [ ] 运行端到端测试
- [ ] 监控 OpenAI API 使用量和成本

---

## MODIFIED Requirements

### MOD-REQ-DIAGNOSIS-004: 诊断任务

**Modified Behavior**:
- 原有：只返回结构化数据
- 修改后：根据 `action_policy` 决定是否生成报告

**Error Handling**:
- 新增：报告生成失败不中断任务
- 新增：记录 `report_error` 字段

---

## Data Model Changes

### DiagnosisResult Model

```python
class DiagnosisResult(BaseModel):
    # ... 现有字段保持不变

    # ADDED: 报告相关字段
    report: Optional[str] = Field(
        None,
        description="LLM 生成的诊断报告（Markdown 格式）"
    )
    report_error: Optional[str] = Field(
        None,
        description="报告生成失败时的错误信息"
    )
```

---

## Open Questions

1. **是否支持报告缓存？**
   - 第一版：不支持，每次都调用 LLM
   - 第二版：根据诊断结果缓存报告（TTL: 24 小时）

2. **是否支持多语言报告？**
   - 第一版：仅中文
   - 第二版：根据用户偏好生成中英文报告

3. **知识库更新频率？**
   - 建议：每周增量更新
   - 自动化：使用 CI/CD 定期运行摄取脚本

---

## Success Metrics

- [x] 知识库摄取脚本成功运行
- [x] RAG 服务能检索相关文档（相似度 > 0.7）
- [x] LLM 生成报告质量评分 > 4.0/5.0（人工评估）
- [x] 报告生成平均耗时 < 5 秒
- [x] 报告生成失败率 < 5%
- [x] 测试覆盖率 > 80%
- [x] 文档完整且可操作
