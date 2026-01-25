# LLM 报告生成系统文档

本文档介绍智能农业诊断系统的 LLM 报告生成功能，包括 Prompt 模板、报告结构、配置选项和成本优化。

## 目录

- [系统概述](#系统概述)
- [Prompt 模板](#prompt-模板)
- [报告结构](#报告结构)
- [配置选项](#配置选项)
- [成本优化](#成本优化)
- [故障排查](#故障排查)

---

## 系统概述

### 工作流程

```
CV 模型诊断结果 (diagnosis_name, confidence, crop_type)
    ↓
RAG 检索相关知识 (相关文档)
    ↓
置信度检查 (confidence < 70% ?)
    ↓
构建 Prompt (模板 + 上下文)
    ↓
LLM 生成报告 (GPT-4o-mini)
    ↓
返回 Markdown 格式报告
```

### 关键特性

- ✅ **上下文感知**: 基于 RAG 检索的农业知识
- ✅ **置信度警告**: 低置信度时提醒用户重新拍照
- ✅ **容错机制**: 报告生成失败不影响诊断结果
- ✅ **结构化输出**: 标准 Markdown 格式，易于渲染

---

## Prompt 模板

### 当前模板

**位置**: `app/worker/chains.py:SIMPLIFIED_REPORT_TEMPLATE`

```python
SIMPLIFIED_REPORT_TEMPLATE = """你是一位农业病虫害诊断专家。请根据以下信息生成一份专业的诊断报告。

## 诊断信息
- **作物类型**: {crop_type}
- **诊断结果**: {diagnosis_name}
- **置信度**: {confidence:.1%}

{confidence_warning}

## 相关知识资料
{context_section}

## 要求
请生成一份结构化的 Markdown 诊断报告，包含以下章节：

1. **病害描述**: 简要描述该病害的病原、主要症状、发病条件
2. **防治措施**: 包括农业防治、生物防治、化学防治（如有推荐药剂，请列出药剂名称、用量、稀释倍数、安全间隔期）
3. **预防措施**: 种植前预防、栽培管理建议、注意事项

请使用专业但易懂的语言，确保农户能够理解并实施。

## 诊断报告
"""
```

### 模板变量说明

| 变量 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `crop_type` | str | 作物类型 | "番茄" |
| `diagnosis_name` | str | 诊断名称 | "番茄晚疫病" |
| `confidence` | float | 置信度 (0-1) | 0.92 |
| `confidence_warning` | str | 置信度警告 | "⚠️ **提示**: 置信度较低（<70%）..." |
| `context_section` | str | RAG 检索的相关知识 | "### 资料 1: late_blight.md\n\n..." |

### 置信度警告规则

```python
def _get_confidence_warning(confidence: float) -> str:
    if confidence < 0.5:
        return "⚠️ **警告**: 置信度很低（<50%），诊断结果可能不准确，强烈建议重新拍照或咨询农业专家。"
    elif confidence < 0.7:
        return "⚠️ **提示**: 置信度较低（<70%），建议重新拍照确认诊断结果。"
    else:
        return ""  # 无警告
```

### 上下文格式化

**函数**: `_format_contexts(contexts: List[Document])`

**输出格式**:
```markdown
### 资料 1: data/knowledge/diseases/late_blight.md

番茄晚疫病由致病疫霉（Phytophthora infestans）引起，属于卵菌门真菌。

### 资料 2: data/knowledge/diseases/late_blight.md

推荐使用68.75%银法利悬浮剂，用量60-75 ml/亩，稀释1500倍液喷雾。
```

**空上下文处理**:
```markdown
**未找到相关资料**。以下报告基于通用知识生成，建议参考专业农业资料确认。
```

---

## 报告结构

### 标准输出格式

LLM 生成的报告遵循以下结构（Markdown 格式）：

```markdown
# 番茄晚疫病诊断报告

## 病害描述
番茄晚疫病由致病疫霉（*Phytophthora infestans*）引起，属于卵菌门真菌。
主要危害叶片和果实。叶片发病初期出现水浸状暗绿色病斑，后扩大为褐色病斑；
果实发病主要在青果期，出现坚硬的褐色斑块。

### 发病条件
- 温度：18-22℃最适宜
- 湿度：相对湿度 >95% 易流行
- 连阴雨天气、雾大露重

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
   - 稀释：1500 倍液喷雾
   - 安全间隔期：3 天

2. **72% 霜脲·锰锌可湿性粉剂**
   - 用量：100-133 g/亩
   - 稀释：600-800 倍液喷雾
   - 安全间隔期：7 天

## 预防措施
- 种植前进行土壤消毒（使用氰氨化钙）
- 加强水肥管理，避免大水漫灌
- 控制种植密度，改善通风条件
- 雨后及时排水，降低田间湿度
- 发病初期摘除病叶，带出田外销毁
```

### 报告字段

在 API 响应中，报告包含在 `DiagnosisResult.report` 字段：

```json
{
  "model_label": "late_blight",
  "confidence": 0.92,
  "diagnosis_name": "番茄晚疫病",
  "category": "Disease",
  "action_policy": "RETRIEVE",
  "report": "# 番茄晚疫病诊断报告\n\n...",  // Markdown 报告
  "report_error": null  // 或错误信息
}
```

---

## 配置选项

### LLM 模型配置

**位置**: `app/worker/chains.py:_get_llm()`

```python
def _get_llm(timeout: int = DEFAULT_TIMEOUT) -> ChatOpenAI:
    """Initialize OpenAI Chat LLM instance."""

    if OPENAI_BASE_URL:
        # 使用自定义 API（如 SiliconFlow）
        llm = ChatOpenAI(
            model=OPENAI_CHAT_MODEL,      # 如 "gpt-4o-mini"
            base_url=OPENAI_BASE_URL,      # 如 "https://api.siliconflow.cn/v1"
            temperature=0.7,
            timeout=timeout,
        )
    else:
        # 使用官方 OpenAI API
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            timeout=timeout,
        )

    return llm
```

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OPENAI_API_KEY` | 必填 | OpenAI/SiliconFlow API 密钥 |
| `OPENAI_BASE_URL` | 可选 | 自定义 API 端点（如 SiliconFlow） |
| `OPENAI_CHAT_MODEL` | `gpt-4o-mini` | 使用的 LLM 模型 |
| `DEFAULT_TIMEOUT` | `30` 秒 | LLM 调用超时时间 |

### 温度参数

```python
temperature=0.7  # 平衡创造性和准确性
```

- **0.0-0.3**: 更确定、更事实性
- **0.4-0.7**: 平衡（推荐）
- **0.8-1.0**: 更创造性、更多样化

### 超时设置

```python
# 在 diagnosis_tasks.py 中
report = generate_diagnosis_report(
    diagnosis_name=...,
    crop_type=...,
    confidence=...,
    contexts=...,
    timeout=30,  # 秒
)
```

**推荐值**:
- 快速响应: 15-20 秒
- 标准响应: 30 秒（默认）
- 复杂报告: 45-60 秒

---

## 成本优化

### 当前成本估算

基于 OpenAI 官方定价（2025年1月）：

| 模型 | 输入 | 输出 | 单次诊断成本 |
|------|------|------|-------------|
| `gpt-4o-mini` | $0.15/1M tokens | $0.60/1M tokens | ~$0.001-0.003 |

**估算示例**:
- 输入: ~800 tokens (Prompt + 3个文档上下文)
- 输出: ~600 tokens (生成的报告)
- 成本: `(800 * 0.15 / 1M) + (600 * 0.60 / 1M)` ≈ **$0.00048** (约 ¥0.0034)

### 使用 SiliconFlow 降低成本

SiliconFlow 提供兼容 OpenAI API 的国内服务：

```bash
# .env 文件配置
OPENAI_BASE_URL=https://api.siliconflow.cn/v1
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
```

**成本对比**:
- OpenAI 官方: $0.00048/次
- SiliconFlow: ≈ ¥0.0005/次（约便宜 80%+）

### 报告缓存策略

```python
# 伪代码：实现报告缓存
def get_cached_report(diagnosis_name, crop_type):
    cache_key = f"{diagnosis_name}_{crop_type}"
    cached = redis.get(cache_key)

    if cached:
        return cached

    # 生成新报告
    report = generate_diagnosis_report(...)
    redis.setex(cache_key, 3600*24, report)  # 缓存 24 小时
    return report
```

**缓存策略**:
- 相同诊断 + 作物 → 使用缓存报告
- 缓存时间: 24 小时
- 适用场景: 高置信度 (>80%) 的常见病害

### 批量生成优化

如果需要批量生成报告：

```python
from concurrent.futures import ThreadPoolExecutor

def batch_generate_reports(diagnoses, max_workers=3):
    """批量生成报告（限制并发数）"""
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for diagnosis in diagnoses:
            future = executor.submit(generate_diagnosis_report, **diagnosis)
            futures.append(future)

        results = [f.result() for f in futures]
    return results
```

**注意事项**:
- 限制并发数避免 API 限流（推荐 3-5）
- 使用指数退避处理 429 错误

### Token 使用监控

```python
# 在 chains.py 中添加 token 计数
from langchain.callbacks import get_openai_callback

def generate_diagnosis_report(...):
    with get_openai_callback() as cb:
        report = chain.invoke(prompt_inputs)

        logger.info(f"Token usage: {cb.total_tokens} tokens")
        logger.info(f"  Prompt: {cb.prompt_tokens} tokens")
        logger.info(f"  Completion: {cb.completion_tokens} tokens")
        logger.info(f"  Cost: ${cb.total_cost:.6f}")

        return report
```

---

## 故障排查

### 常见错误

#### 1. 超时错误

**错误**:
```
ReportTimeoutError: LLM call timed out: Request timed out
```

**解决方案**:
- 增加 `timeout` 参数: `timeout=45`
- 检查网络连接
- 切换到更快的 API 端点（如 SiliconFlow）

#### 2. API 限流

**错误**:
```
LLMError: API rate limit exceeded: 429 Too Many Requests
```

**解决方案**:
```python
# 实现指数退避重试
import time

def generate_with_retry(diagnosis_name, crop_type, confidence, contexts, max_retries=3):
    for attempt in range(max_retries):
        try:
            return generate_diagnosis_report(
                diagnosis_name, crop_type, confidence, contexts, timeout=30
            )
        except LLMError as e:
            if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1, 2, 4 秒
                time.sleep(wait_time)
                continue
            raise
```

#### 3. 认证失败

**错误**:
```
LLMError: API authentication failed: 401 Unauthorized
```

**解决方案**:
```bash
# 验证 API 密钥
echo $OPENAI_API_KEY

# 测试 API 连接
curl https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"test"}]}'
```

#### 4. 报告格式错误

**症状**: LLM 返回的内容不是有效的 Markdown

**解决方案**:
- 在 Prompt 中明确要求 Markdown 格式
- 使用更低的 `temperature` (0.3-0.5)
- 添加输出示例（Few-shot prompting）

**改进 Prompt**:
```python
template += """

## 输出格式示例

# 番茄早疫病诊断报告

## 病害描述
...

## 防治措施
...

请严格按照上述格式输出。
"""
```

#### 5. 空报告

**症状**: `report` 为空字符串或 None

**可能原因**:
- LLM 返回空内容
- 上下文为空且 LLM 无法生成通用建议

**调试**:
```python
# 在 chains.py 中添加日志
logger.info(f"LLM response: {repr(report)}")

if not report or report.strip() == "":
    logger.warning("LLM returned empty report, using fallback")
    return "# 诊断报告\n\n暂时无法生成详细报告，请咨询农业专家。"
```

---

## 最佳实践

### Prompt 编写

1. **清晰的角色定义**: "你是一位农业病虫害诊断专家"
2. **具体的输出要求**: 明确要求 Markdown 格式
3. **提供上下文**: 包含 RAG 检索的相关知识
4. **设置置信度警告**: 低置信度时提醒用户

### 错误处理

```python
try:
    report = generate_diagnosis_report(...)
except ReportTimeoutError as e:
    # 超时：使用简化报告
    report = f"# {diagnosis_name}\n\n报告生成超时，请稍后重试。"
    logger.error(f"Timeout: {e}")
except LLMError as e:
    # API 错误：不中断诊断流程
    report = None
    report_error = str(e)
    logger.error(f"LLM error: {e}")
except Exception as e:
    # 未知错误：记录并继续
    report = None
    report_error = f"Unexpected error: {str(e)}"
    logger.exception("Unexpected error")
```

### 性能监控

```python
import time

def generate_diagnosis_report(...):
    start_time = time.time()

    try:
        report = chain.invoke(prompt_inputs)
        elapsed = time.time() - start_time

        logger.info(f"Report generated in {elapsed:.2f}s")
        logger.info(f"Report length: {len(report)} chars")

        # 性能告警
        if elapsed > 20:
            logger.warning(f"Slow report generation: {elapsed:.2f}s")

        return report

    except Exception as e:
        logger.error(f"Report generation failed after {time.time() - start_time:.2f}s")
        raise
```

---

## 相关文档

- [知识库 RAG 指南](./knowledge_rag.md)
- [诊断工作流程](./diagnosis_workflow.md)

---

## 更新日志

- **2025-01-25**: 初始版本，支持 GPT-4o-mini 和 SiliconFlow
- 未来计划：支持本地模型（Llama、Qwen）
