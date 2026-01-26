# Implementation Tasks: implement-knowledge-rag

**Change ID**: `implement-knowledge-rag`
**Status**: Implementation Complete ✅

---

## Task Checklist

### Phase 1: 环境准备和依赖管理 (REQ-RAG-001) ✅

- [x] **T1.1**: 在 `.env` 文件中添加 `OPENAI_API_KEY` 配置
- [x] **T1.2**: 运行 `uv add chromadb langchain langchain-openai openai pypdf unstructured tiktoken`
- [x] **T1.3**: 运行 `uv sync` 同步依赖
- [x] **T1.4**: 创建 `data/knowledge/` 目录
- [x] **T1.5**: 创建 `data/chroma/` 目录
- [x] **T1.6**: 创建 `data/knowledge/` 示例文件目录和内容：

  **文件结构**:
  ```
  data/knowledge/
  ├── diseases/
  │   ├── powdery_mildew.md
  │   └── late_blight.md
  └── crops/
      └── tomato.md
  ```

  **文件 1: `data/knowledge/diseases/powdery_mildew.md`**
  ```markdown
  # 番茄白粉病

  ## 病原
  番茄白粉病由真菌 Sphaerotheca fuliginea 引起，属于子囊菌亚门真菌。

  ## 症状
  主要危害叶片，也可危害茎、果柄等。发病初期叶片出现白色粉状小霉点，
  后期扩大连成白色粉状霉层，严重时叶片枯黄卷曲。

  ## 发病条件
  - 温度：20-25℃最适宜
  - 湿度：相对湿度 50%-80%易发病
  - 栽培过密、通风不良
  - 氮肥过多、植株徒长

  ## 防治措施

  ### 农业防治
  - 选用抗病品种
  - 合理密植，改善通风透光条件
  - 避免过量施氮肥
  - 及时清除病残体

  ### 生物防治
  - 发病初期喷施枯草芽孢杆菌制剂，稀释 500-800 倍
  - 释放天敌昆虫（如瓢虫）控制蚜虫传播

  ### 化学防治
  发病初期及时用药，每 7-10 天喷 1 次，连续 2-3 次。

  推荐药剂：
  1. **25% 三唑酮可湿性粉剂**
     - 用量：50-75 g/亩
     - 稀释 1500-2000 倍液喷雾
     - 安全间隔期：7 天

  2. **10% 苯醚甲环唑水分散粒剂**
     - 用量：30-50 g/亩
     - 稀释 1500 倍液喷雾
     - 安全间隔期：3-5 天

  3. **40% 氟硅唑乳油**
     - 用量：15-20 ml/亩
     - 稀释 6000-8000 倍液喷雾
     - 注意：避免高温时段施药

  ## 预防措施
  - 种植前进行种子消毒（55℃温水浸种 15 分钟）
  - 保持棚室内通风，降低湿度
  - 控制种植密度，避免过密
  - 增施有机肥，提高植株抗病力
  - 定期检查，发现病叶及时摘除
  ```

  **文件 2: `data/knowledge/diseases/late_blight.md`**
  ```markdown
  # 番茄晚疫病

  ## 病原
  番茄晚疫病由致病疫霉（Phytophthora infestans）引起，属于卵菌门真菌。

  ## 症状
  主要危害叶片和果实。叶片发病初期出现水浸状暗绿色病斑，后扩大为褐色病斑；
  果实发病主要在青果期，出现坚硬的褐色斑块，湿度大时病部产生白色霉层。

  ## 发病条件
  - 温度：18-22℃最适宜
  - 湿度：相对湿度 >95% 易流行
  - 连阴雨天气、雾大露重
  - 种植密度过大、通风不良

  ## 防治措施

  ### 农业防治
  - 选用抗病品种（如"中杂9号"、"佳粉15号"）
  - 实行轮作，避免与茄科作物连作
  - 加强通风，降低棚内湿度
  - 及时清除中心病株

  ### 生物防治
  - 喷施哈茨木霉菌制剂，稀释 500 倍
  - 使用枯草芽孢杆菌，预防效果较好

  ### 化学防治
  发现中心病株立即用药，每 5-7 天喷 1 次，连续 3-4 次。

  推荐药剂：
  1. **68.75% 银法利悬浮剂（氟菌·霜霉威）**
     - 用量：60-75 ml/亩
     - 稀释 1500 倍液喷雾
     - 安全间隔期：3 天
     - 注意：早晚施药效果更佳

  2. **72% 霜脲·锰锌可湿性粉剂**
     - 用量：100-133 g/亩
     - 稀释 600-800 倍液喷雾
     - 安全间隔期：7 天
     - 注意：避免高温时段施药

  3. **50% 烯酰吗啉可湿性粉剂**
     - 用量：30-40 g/亩
     - 稀释 1500 倍液喷雾
     - 安全间隔期：5 天

  ## 预防措施
  - 种植前进行土壤消毒（使用氰氨化钙）
  - 加强水肥管理，避免大水漫灌
  - 控制种植密度，改善通风条件
  - 雨后及时排水，降低田间湿度
  - 发病初期摘除病叶，带出田外销毁
  ```

  **文件 3: `data/knowledge/crops/tomato.md`**
  ```markdown
  # 番茄栽培管理

  ## 品种选择
  根据栽培季节和用途选择品种：
  - **春季早熟栽培**：选择耐低温弱光、早熟品种（如"金棚1号"、"辽粉杂3号"）
  - **秋季延后栽培**：选择抗病毒、耐热品种（如"中杂9号"、"毛粉802"）
  - **温室越冬栽培**：选择耐弱光、连续结果能力强的品种

  ## 育苗技术
  - **播种期**：根据栽培季节确定，一般提前 50-60 天育苗
  - **种子处理**：55℃温水浸种 15 分钟，或 10% 磷酸三钠溶液浸种 20 分钟
  - **苗床管理**：白天温度 25-28℃，夜间 15-18℃
  - **分苗**：2-3 片真叶时分苗，株行距 10×10 cm

  ## 定植
  - **定植时间**：当幼苗达到 6-7 片真叶，株高 20-25 cm 时定植
  - **定植密度**：
    - 早熟品种：3500-4000 株/亩
    - 中晚熟品种：3000-3500 株/亩
  - **定植方法**：起垄栽培，垄宽 70 cm，高 15-20 cm，双行种植

  ## 肥水管理
  ### 施肥原则
  - 基肥为主，追肥为辅
  - 有机肥与化肥配合施用
  - 控制氮肥，增施磷钾肥

  ### 推荐施肥量（每亩）
  - **基肥**：腐熟有机肥 3000-5000 kg，复合肥 50 kg
  - **追肥**：
    - 第 1 穗果膨大期：尿素 10 kg + 硫酸钾 10 kg
    - 第 2-3 穗果膨大期：复合肥 15 kg + 硫酸钾 10 kg

  ### 水分管理
  - 定植后浇足定植水
  - 开花前适当控水，促进根系发育
  - 结果期保持土壤湿润，小水勤浇
  - 避免大水漫灌，防止病害发生

  ## 整枝打杈
  - **整枝方式**：单干整枝或双干整枝
  - **搭架绑蔓**：株高 30 cm 时搭架，以后每隔 30 cm 绑蔓一次
  - **打杈**：及时去除侧芽，保留主干
  - **摘心**：保留 4-5 穗果后摘心，促进果实成熟

  ## 病虫害防治
  主要病虫害及防治方法详见具体病害文档：
  - 晚疫病
  - 早疫病
  - 灰霉病
  - 叶霉病
  - 病毒病
  - 蚜虫
  - 白粉虱
  - 棉铃虫

  ## 采收
  - **采收标准**：果实充分着色，但未软化
  - **采收时间**：早晚气温低时采收，避免中午高温时段
  - **采收方法**：一手托住果实，一手折断果柄，避免损伤植株
  ```

### Phase 2: 知识库摄取脚本 (REQ-RAG-002) ✅

- [x] **T2.1**: 创建 `scripts/ingest_knowledge.py` 文件
- [x] **T2.2**: 实现 CLI 参数解析：
  - `--path` (默认: `data/knowledge/`)
  - `--append` (增量模式)
  - `--reset` (重置数据库)
  - `--chunk-size` (默认: 1000)
  - `--overlap` (默认: 200)
- [x] **T2.3**: 实现 Markdown 文件加载：
  - 使用 `langchain.document_loaders.DirectoryLoader`
  - 使用 `langchain.document_loaders.UnstructuredMarkdownLoader`
  - 支持递归扫描子目录
- [x] **T2.4**: 实现 PDF 文件加载：
  - 使用 `langchain.document_loaders.PyPDFLoader`
  - 处理多页 PDF
- [x] **T2.5**: 实现文档切片：
  - 使用 `langchain.text_splitter.RecursiveCharacterTextSplitter`
  - 配置 `chunk_size` 和 `overlap`
  - 保留文档元数据（source, page, category）
- [x] **T2.6**: 实现 ChromaDB 向量存储：
  - 使用 `langchain.vectorstores.Chroma`
  - 配置持久化目录 `data/chroma/`
  - 使用 OpenAI Embeddings (`text-embedding-3-small`)
- [x] **T2.7**: 实现 `--reset` 逻辑：
  - 删除 `data/chroma/` 目录
  - 重新创建空数据库
- [x] **T2.8**: 实现 `--append` 逻辑：
  - 加载现有 ChromaDB 实例
  - 添加新文档到现有数据
- [x] **T2.9**: 添加统计输出：
  - 文件数量
  - 切片数量
  - 用时（秒）
  - ChromaDB 路径
- [x] **T2.10**: 添加错误处理：
  - 文件不存在警告
  - 空目录警告
  - API 密钥未配置错误
- [x] **T2.11**: 添加完整的 docstring 和使用示例
- [x] **T2.12**: 测试摄取脚本：
  - 运行 `uv run python scripts/ingest_knowledge.py --path data/knowledge/`
  - 验证 `data/chroma/` 目录创建
  - 验证输出统计信息
- [x] **T2.13**: **关键验证** - 运行 ingest 脚本处理示例文件，确保不报错：
  ```bash
  # 确保示例文件存在
  ls -la data/knowledge/diseases/powdery_mildew.md

  # 运行摄取脚本
  uv run python scripts/ingest_knowledge.py --path data/knowledge/

  # 验证输出
  # ✅ Processed 1 files
  # ✅ Created N chunks
  # ✅ Stored in ChromaDB: data/chroma/
  # ✅ Time elapsed: X.Xs

  # 验证 ChromaDB 目录创建
  ls -la data/chroma/

  # 如果出错，立即修复（不要等到集成测试）
  ```

### Phase 3: RAG 服务封装 (REQ-RAG-003)

- [x] **T3.1**: 创建 `app/services/rag_service.py` 文件
- [x] **T3.2**: 定义 `RAGServiceNotInitializedError` 异常类
- [x] **T3.3**: 实现 `RAGService` 类：
  - Singleton 模式（使用 `__new__` 或模块级变量）
  - `__init__`: 初始化 ChromaDB 客户端
  - `query`: 向量检索方法
- [x] **T3.4**: 实现 `_get_chroma_db()` 私有方法：
  - 从持久化目录加载 ChromaDB
  - 配置 OpenAI Embeddings
  - 抛出 `RAGServiceNotInitializedError` 如果数据库不存在
- [x] **T3.5**: 实现 `query()` 方法：
  - 参数：`query_text: str`, `top_k: int = 3`, `filter_metadata: Optional[Dict] = None`
  - 调用 `chroma_db.similarity_search(query_text, k=top_k, filter=filter_metadata)`
  - 返回 `List[Document]`
- [x] **T3.6**: 实现 `get_rag_service()` 单例函数：
  - 模块级 `_instance` 变量
  - 懒加载模式（首次调用时初始化）
- [x] **T3.7**: 添加详细的日志记录：
  - 初始化日志
  - 查询日志（query_text, top_k, 结果数）
  - 错误日志
- [x] **T3.8**: 添加完整的 docstring 和类型提示
- [ ] **T3.9**: 在 `app/core/deps.py` 中添加 `depends_rag` 依赖注入函数（可选）
- [x] **T3.10**: **关键验证** - 运行 RAG 服务单元测试，确保基础功能正常：
  ```bash
  # 确保测试文件存在
  ls -la tests/services/test_rag_service.py

  # 运行 RAG 服务测试
  uv run pytest tests/services/test_rag_service.py -v

  # 验证所有测试通过
  # ✅ test_rag_service_init PASSED
  # ✅ test_query_success PASSED
  # ✅ test_query_with_filter PASSED
  # ✅ test_query_empty_result PASSED
  # ✅ test_singleton_pattern PASSED

  # 如果测试失败，立即修复（不要等到集成测试）
  ```

### Phase 4: LLM 报告生成链 (REQ-RAG-004)

- [x] **T4.1**: 创建 `app/worker/chains.py` 文件
- [x] **T4.2**: 实现 `_get_llm()` 私有函数：
  - 使用 `langchain_openai.ChatOpenAI`
  - 模型：`gpt-4o-mini`
  - 温度：`0.7`（平衡创造性和准确性）
  - 超时：`timeout=30`
- [x] **T4.3**: 定义 `REPORT_TEMPLATE` Prompt 模板：
  - 角色：农业病虫害诊断专家
  - 输入：diagnosis_name, crop_type, confidence, contexts
  - 输出结构：病害描述、防治措施、推荐药剂、预防措施
  - 格式：Markdown
- [x] **T4.4**: 实现 `generate_diagnosis_report()` 函数：
  - 参数：`diagnosis_name, crop_type, confidence, contexts, llm=None, timeout=30`
  - 使用 `langchain.prompts.PromptTemplate`
  - 使用 `langchain.chains.LLMChain`
- [x] **T4.5**: 实现置信度低警告：
  - 如果 `confidence < 0.7`：在报告中添加 "⚠️ 置信度较低，建议重新拍照"
  - 如果 `confidence < 0.5`：添加 "⚠️ 置信度很低，诊断结果可能不准确"
- [x] **T4.6**: 实现上下文为空处理：
  - 如果 `contexts = []`：在 Prompt 中提示 "未找到相关资料，基于通用知识生成"
- [x] **T4.7**: 添加超时处理：
  - 使用 `func_timeout` 或 `signal.alarm`
  - 超时后抛出 `TimeoutError`
- [x] **T4.8**: 添加异常处理：
  - 捕获 `openai.APIError`
  - 捕获 `openai.RateLimitError`
  - 捕获 `openai.AuthenticationError`
  - 统一转换为自定义 `LLMError`
- [x] **T4.9**: 添加详细的日志记录：
  - LLM 调用开始/结束
  - Token 使用量
  - 超时和错误日志
- [x] **T4.10**: 添加完整的 docstring 和类型提示
- [x] **T4.11**: **关键验证** - 运行报告生成链单元测试，确保 LLM 调用正常：
  ```bash
  # 确保 OpenAI API Key 已配置
  echo $OPENAI_API_KEY | cut -c1-10

  # 运行报告生成链测试
  uv run pytest tests/worker/test_chains.py -v

  # 验证所有测试通过
  # ✅ test_generate_report_success PASSED
  # ✅ test_generate_report_timeout PASSED
  # ✅ test_generate_report_empty_contexts PASSED
  # ✅ test_generate_report_low_confidence PASSED
  # ✅ test_generate_report_api_error PASSED

  # 检查 LLM 调用成本（第一次测试会消耗少量 API 配额）
  # 如果测试失败，检查 API Key 和网络连接
  ```

### Phase 5: 诊断任务集成 (REQ-RAG-005) ✅

- [x] **T5.1**: 修改 `app/models/diagnosis.py`：
  - 在 `DiagnosisResult` 中添加 `report: Optional[str]` 字段
  - 在 `DiagnosisResult` 中添加 `report_error: Optional[str]` 字段
- [x] **T5.2**: 修改 `app/worker/diagnosis_tasks.py`：
  - 导入 `get_rag_service` 和 `generate_diagnosis_report`
- [x] **T5.3**: 在 `analyze_image` 任务中添加报告生成逻辑：
  - 查询 Taxonomy 后检查 `entry.action_policy`
  - 如果 `action_policy == "RETRIEVE"`：
    - 调用 `rag.query()`
    - 调用 `generate_diagnosis_report()`
    - 将报告添加到结果
- [x] **T5.4**: 添加报告生成异常处理：
  - 使用 `try-except` 包裹报告生成逻辑
  - 捕获 `TimeoutError`, `LLMError`, `RAGServiceNotInitializedError`
  - 记录错误日志：`logger.error(f"Failed to generate report: {str(e)}")`
  - 设置 `result["report"] = None`
  - 设置 `result["report_error"] = str(e)`
- [x] **T5.5**: 添加报告生成日志：
  - 开始：`logger.info(f"Generating report for {diagnosis_name}...")`
  - 成功：`logger.info(f"Report generated successfully ({len(report)} chars)")`
  - 失败：`logger.error(f"Report generation failed: {error}")`
- [x] **T5.6**: 测试诊断任务：
  - 运行 Celery Worker
  - 提交诊断请求
  - 验证报告生成
- [x] **T5.7**: **关键验证** - 运行端到端集成测试，确保整个流程打通：
  ```bash
  # 确保所有服务运行
  # Redis: docker-compose up -d redis
  # MinIO: docker-compose up -d minio
  # Celery Worker: celery -A app.worker.celery_app worker --loglevel=info

  # 确保知识库已初始化
  uv run python scripts/ingest_knowledge.py --path data/knowledge/

  # 运行集成测试
  uv run pytest tests/integration/test_rag_e2e.py -v -s

  # 验证输出包含完整的诊断报告
  # ✅ Diagnosis result includes report
  # ✅ Report contains: 病害描述, 防治措施, 推荐药剂, 预防措施

  # 手动验证：上传真实图片，检查报告质量
  ```

### Phase 6: 测试和验证 (REQ-RAG-006) ✅

#### RAG 服务测试

- [x] **T6.1**: 创建 `tests/services/test_rag_service.py` 文件
- [x] **T6.2**: 实现 `test_rag_service_init()`：
  - 测试 ChromaDB 初始化
  - 测试数据库不存在时抛出异常
- [x] **T6.3**: 实现 `test_query_success()`：
  - Mock ChromaDB
  - 测试返回相关文档
  - 验证 top_k 参数
- [x] **T6.4**: 实现 `test_query_with_filter()`：
  - 测试元数据过滤
  - 验证过滤条件生效
- [x] **T6.5**: 实现 `test_query_empty_result()`：
  - Mock 返回空列表
  - 验证不抛出异常
- [x] **T6.6**: 实现 `test_singleton_pattern()`：
  - 多次调用 `get_rag_service()`
  - 验证返回同一实例

#### 报告生成链测试

- [x] **T6.7**: 创建 `tests/worker/test_chains.py` 文件
- [x] **T6.8**: 实现 `test_generate_report_success()`：
  - Mock OpenAI LLM
  - 测试返回完整报告
  - 验证报告包含必需章节
- [x] **T6.9**: 实现 `test_generate_report_timeout()`：
  - Mock LLM 超时
  - 验证抛出 `TimeoutError`
- [x] **T6.10**: 实现 `test_generate_report_empty_contexts()`：
  - 传入空 `contexts = []`
  - 验证报告包含 "未找到相关资料"
- [x] **T6.11**: 实现 `test_generate_report_low_confidence()`：
  - 传入 `confidence = 0.55`
  - 验证报告包含置信度警告
- [x] **T6.12**: 实现 `test_generate_report_api_error()`：
  - Mock OpenAI API 错误
  - 验证抛出 `LLMError`

#### 诊断任务集成测试

- [x] **T6.13**: 在 `tests/worker/test_diagnosis_tasks_rag.py` 中添加新测试：
- [x] **T6.14**: 实现 `test_analyze_image_with_report()`：
  - Mock RAG 和 LLM
  - 测试报告成功生成
  - 验证 `result["report"]` 不为空
- [x] **T6.15**: 实现 `test_analyze_image_skip_report_healthy()`：
  - Mock Taxonomy 返回 `action_policy = "PASS"`
  - 验证不调用 RAG 和 LLM
  - 验证 `result["report"]` 为 `None`
- [x] **T6.16**: 实现 `test_analyze_image_rag_failure()`：
  - Mock RAG 抛出异常
  - 验证任务不中断
  - 验证 `result["report_error"]` 设置
- [x] **T6.17**: 实现 `test_analyze_image_llm_timeout()`：
  - Mock LLM 超时
  - 验证任务不中断
  - 验证 `result["report_error"]` 包含 "Timeout"

#### 端到端测试

- [x] **T6.18**: 创建 `tests/integration/test_rag_e2e.py` 文件
- [x] **T6.19**: 实现 `test_end_to_end_rag_diagnosis()`：
  - 启动所有服务（FastAPI, Celery, ChromaDB）
  - 运行知识库摄取
  - 上传测试图片
  - 提交诊断
  - 轮询结果
  - 验证报告生成
- [x] **T6.20**: 运行所有测试：
  - `uv run pytest tests/services/test_rag_service.py -v`
  - `uv run pytest tests/worker/test_chains.py -v`
  - `uv run pytest tests/worker/test_diagnosis_tasks_rag.py -v`
  - `uv run pytest tests/integration/test_rag_e2e.py -v -m integration`
- [x] **T6.21**: 验证测试覆盖率 > 80%：
  - `uv run pytest --cov=app.services.rag_service --cov=app.worker.chains --cov-report=term-missing`

### Phase 7: 文档和部署 (REQ-RAG-007) ✅

- [x] **T7.1**: 创建 `docs/knowledge_rag.md` 文档：
  - 知识库管理指南
  - 摄取脚本使用说明
  - ChromaDB 管理和备份
  - 故障排查
- [x] **T7.2**: 创建 `docs/report_generation.md` 文档：
  - Prompt 模板说明
  - 报告结构定义
  - 自定义配置（温度、超时等）
  - 成本优化建议
- [x] **T7.3**: 更新 `docs/diagnosis_workflow.md`：
  - 添加报告生成章节
  - 更新数据模型说明
  - 添加故障排查
- [x] **T7.4**: 创建示例知识库文档：
  - `data/knowledge/diseases/powdery_mildew.md`
  - `data/knowledge/diseases/late_blight.md`
  - `data/knowledge/crops/tomato.md`
- [x] **T7.5**: 更新 `README.md`：
  - 添加 RAG 系统介绍
  - 添加环境变量说明
  - 添加快速开始指南
- [x] **T7.6**: 创建部署检查清单：
  - 环境变量配置
  - 知识库初始化
  - 服务启动顺序
  - 健康检查
- [x] **T7.7**: 运行手动测试：
  - 完整诊断流程
  - 报告质量评估
  - 性能测试（响应时间）

---

## Task Dependencies

```
T1.x (环境准备)
    ↓
T2.x (摄取脚本) → T2.13: ✅ 验证 ingest 脚本
    ↓
T3.x (RAG 服务) → T3.10: ✅ 验证 RAG 服务测试
    ↓
T4.x (报告生成链) → T4.11: ✅ 验证 LLM 调用
    ↓
T5.x (诊断任务集成) → T5.7: ✅ 验证端到端流程
    ↓
T6.x (完整测试覆盖)
    ↓
T7.x (文档和部署)
```

**Critical Path**: T1.2 → T2.6 → T2.13 → T3.5 → T3.10 → T4.4 → T4.11 → T5.3 → T5.7

**步步为营验证点**：
- **T2.13**: 摄取脚本必须成功运行，确保 ChromaDB 可用
- **T3.10**: RAG 服务测试通过，确保向量检索正常
- **T4.11**: LLM 调用测试通过，确保 OpenAI API 可用
- **T5.7**: 端到端测试通过，确保整个流程打通

---

## Progressive Verification Strategy (步步为营)

本提案采用**渐进式验证策略**，在每个关键阶段结束时立即验证，避免等到最后才发现问题。

### 验证时机

| 阶段 | 验证点 | 目的 | 验证方法 |
|------|--------|------|----------|
| **Phase 2** | **T2.13** | 确保摄取脚本可用 | 运行 `ingest_knowledge.py` 处理示例文件，检查 ChromaDB |
| **Phase 3** | **T3.10** | 确保向量检索可用 | 运行 `test_rag_service.py`，验证查询功能 |
| **Phase 4** | **T4.11** | 确保 LLM 调用可用 | 运行 `test_chains.py`，验证报告生成 |
| **Phase 5** | **T5.7** | 确保端到端流程打通 | 运行 `test_rag_e2e.py`，验证完整诊断流程 |

### 失败处理

如果任何验证点失败：
1. **立即停止** - 不要继续下一个阶段
2. **分析原因** - 检查日志，定位问题
3. **修复问题** - 调整代码或配置
4. **重新验证** - 直到验证通过
5. **记录经验** - 更新文档，避免重复问题

### 为什么步步为营？

❌ **错误做法**：等到最后才测试
```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → ❌ 集成测试失败
                                              ↑
                                        浪费大量时间排查
```

✅ **正确做法**：每个阶段验证
```
Phase 1 → Phase 2 → ✅ T2.13 验证通过
       → Phase 3 → ✅ T3.10 验证通过
       → Phase 4 → ✅ T4.11 验证通过
       → Phase 5 → ✅ T5.7 验证通过
       → 集成测试 ✅ 轻松通过
```

---

## Definition of Done

A task is marked `[x]` when:
1. The code is written and passes linting (black, ruff)
2. No Pylance/Pyflakes warnings
3. Unit tests pass
4. Documentation is updated (if applicable)
5. Manual testing confirms functionality (for critical paths)

---

## Notes

- **T2.6**: ChromaDB 持久化目录默认为 `data/chroma/`，可通过环境变量 `CHROMA_PERSIST_DIRECTORY` 自定义
- **T4.3**: Prompt 模板使用中文，因为知识库和用户都是中文场景
- **T5.4**: 关键设计：报告生成失败**不能**导致整个任务崩溃，只记录错误信息
- **T6.19**: 端到端测试需要真实运行所有服务，不能使用 TestClient
- **T7.1**: 知识库文档建议由农业专家编写或审核，确保准确性

---

## Extreme Conditions to Test

### 摄取脚本极端条件
- [ ] 空目录
- [ ] 不支持的文件格式（.txt, .docx）
- [ ] 超大文件（>10MB PDF）
- [ ] 损坏的 PDF 文件
- [ ] 编码错误的 Markdown
- [ ] API 密钥无效
- [ ] 网络超时

### RAG 服务极端条件
- [ ] 数据库未初始化
- [ ] 空查询字符串
- [ ] 超长查询（>1000 字符）
- [ ] 并发查询（10 个并发）
- [ ] 元数据过滤条件无效

### 报告生成极端条件
- [ ] 空上下文
- [ ] 超多上下文（>10 个文档）
- [ ] 置信度为 0 或 1
- [ ] 超长诊断名称
- [ ] OpenAI API 超时
- [ ] OpenAI API 限流（429）
- [ ] OpenAI API 认证失败
- [ ] LLM 输出格式错误（非 Markdown）

### 诊断任务极端条件
- [ ] RAG 服务未初始化
- [ ] LLM 调用超时
- [ ] OpenAI API 密钥未配置
- [ ] 报告生成失败（各种原因）
- [ ] 并发诊断任务（10 个并发）

---

## Verification Checklist

完成实现后，请验证以下内容：

- [ ] 知识库摄取脚本成功运行并生成向量
- [ ] RAG 服务能检索相关文档（相似度合理）
- [ ] LLM 成功生成结构化诊断报告
- [ ] 报告包含所有必需章节（描述、防治、药剂、预防）
- [ ] 健康样本不生成报告（`action_policy == "IGNORE"`）
- [ ] 报告生成失败不中断诊断任务
- [ ] 所有测试通过（覆盖率 > 80%）
- [ ] 代码无 linting 错误
- [ ] 无类型提示警告
- [ ] 日志记录完整（RAG 查询、LLM 调用、错误）
- [ ] 文档完整且可操作
- [ ] 手动测试端到端流程成功
- [ ] OpenAI API 使用量和成本在可接受范围

---

## System Requirements

完成此变更需要以下服务运行：

```bash
# 1. 配置环境变量
export OPENAI_API_KEY="sk-..."

# 2. 初始化知识库（一次性）
uv run python scripts/ingest_knowledge.py --path data/knowledge/

# 3. 启动基础设施
docker-compose up -d redis minio

# 4. 启动 Celery Worker
celery -A app.worker.celery_app worker --loglevel=info

# 5. 启动 FastAPI
uv run uvicorn app.api.main:app --reload
```

---

## Completion Summary

**待填充**：实现完成后更新此部分。

---

## Next Steps

- 第一版：OpenAI Embeddings + GPT-4o-mini
- 第二版：本地 BGE-M3 Embeddings（降低成本）
- 第三版：报告缓存（减少 LLM 调用）
- 第四版：多语言支持（中英文报告）
- 第五版：批量报告生成（支持批量诊断）
