# Product Requirements Document (PRD)
# 项目名称：实验室植物病虫害智能诊断 Agent (Lab-Pest-Agent)
# 版本：v1.0 (MVP)

## 1. 项目背景与目标 (Context)
本系统旨在为农业实验室提供一个自动化的病虫害诊断工具。通过集成现有的视觉识别算法（CV）和基于检索增强生成（RAG）的专家知识库，实现从“图像上传”到“防治报告生成”的全流程自动化。

**核心目标 (MVP Goals)**：
1.  实现视觉算法与大语言模型的有效串联。
2.  通过 RAG 技术解决大模型在农药推荐上的“幻觉”问题。
3.  提供异步任务处理机制，应对高延迟的算法推理。
4.  提供一个极简的验证性前端（Streamlit）。

---

## 2. 用户角色 (User Personas)
* **实验室研究员/农技员**：
    * 输入：上传作物叶片照片，选择作物种类（如草莓、番茄）。
    * 期望：获得准确的病害名称、置信度、以及基于权威文档的防治方案（物理+化学）。
    * 痛点：不需要花哨的 UI，只需要结果准确、系统稳定。

---

## 3. 核心功能需求 (Functional Requirements)

### 3.1. 诊断提交接口 (Diagnosis Submission)
* **功能**：接收前端上传的图片和元数据。
* **输入**：
    * `image_url`: 图片地址（经 MinIO/OSS 处理后）。
    * `crop_context`: 作物种类（用于缩小检索范围）。
* **逻辑**：
    * 系统生成唯一 `task_id`。
    * 将任务推入 Redis 队列。
    * **立即返回** `task_id` 和状态 `pending`，不等待推理结束。

### 3.2. 智能分析核心 (Analysis Core - Worker)
这是系统的“大脑”，由 Celery Worker 执行。
1.  **视觉识别 (CV Step)**：
    * 调用算法组 API。
    * 获取 `class_id`, `confidence`。
    * **关键约束**：必须通过 `data/taxonomy_standard_v1.json` 将 `class_id` 映射为标准中文学名（如 "Tetranychus cinnabarinus" -> "朱砂叶螨"）。
2.  **置信度过滤 (Gatekeeper)**：
    * 如果 `confidence < 0.6`，标记任务为 `review_needed`，跳过 RAG，直接返回“无法确定，请人工复核”。
3.  **知识检索 (RAG Step)**：
    * 使用映射后的标准学名去 ChromaDB 检索。
    * 检索维度：`病理特征`, `物理防治`, `化学防治 (需包含安全间隔期)`。
4.  **报告生成 (Synthesis)**：
    * LLM 输入：CV 结果 + RAG 检索到的文本块。
    * LLM 输出：结构化 JSON 报告。

### 3.3. 结果查询 (Result Polling)
* **功能**：前端轮询任务状态。
* **输出**：
    * 状态：`processing` | `success` | `failed`。
    * 数据：包含病害名称、置信度、防治措施列表（数组格式）。

### 3.4. 前端展示 (Streamlit UI)
* **页面布局**：
    * 左侧：图片上传区 + 作物下拉选框。
    * 右侧：实时状态进度条 -> 最终诊断卡片。
* **交互**：点击“开始诊断”后，自动轮询后端接口，直到出结果。

---

## 4. 数据与存储要求 (Data Schema)

### 4.1. 核心实体：`DiagnosisTask` (PostgreSQL)
| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `task_id` | UUID | 主键 |
| `status` | Enum | PENDING, PROCESSING, SUCCESS, FAILED |
| `image_url` | String | 图片链接 |
| `cv_result_raw` | JSON | 算法组返回的原始数据（留底备查） |
| `diagnosis_final`| JSON | 最终生成的结构化报告 |
| `created_at` | DateTime | 创建时间 |

---

## 5. 非功能性需求 (NFRs)
1.  **响应性**：提交接口响应时间 < 200ms。
2.  **容错性**：如果 CV 服务超时（>15s），Worker 应捕获异常并标记任务为 Failed，而不是让整个 Worker 崩溃。
3.  **准确性**：严禁 LLM 编造不存在的农药名称（必须基于 RAG 内容）。
4.  **一致性**：所有代码变更必须遵循 `openspec/project.md` 定义的技术栈。