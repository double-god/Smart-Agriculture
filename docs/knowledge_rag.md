# 知识库 RAG 系统使用指南

本文档介绍如何管理农业知识库、使用 RAG（检索增强生成）系统以及相关故障排查。

## 目录

- [系统概述](#系统概述)
- [知识库管理](#知识库管理)
- [摄取脚本使用](#摄取脚本使用)
- [ChromaDB 管理](#chromadb-管理)
- [故障排查](#故障排查)

---

## 系统概述

RAG 系统包含以下组件：

### 架构

```
知识文件 (Markdown/PDF)
    ↓
摄取脚本 (ingest_knowledge.py)
    ↓
文档切片 (Chunking)
    ↓
向量化 (OpenAI Embeddings)
    ↓
ChromaDB (向量数据库)
    ↓
RAG Service (检索服务)
    ↓
LLM (报告生成)
```

### 技术栈

- **向量数据库**: ChromaDB
- **嵌入模型**: OpenAI `text-embedding-3-small` / SiliconFlow Qwen3-Embedding-0.6B
- **语言模型**: GPT-4o-mini
- **文档格式**: Markdown, PDF

---

## 知识库管理

### 知识库目录结构

```
data/knowledge/
├── diseases/           # 病害知识
│   ├── powdery_mildew.md
│   ├── late_blight.md
│   └── ...
├── pests/              # 害虫知识
│   ├── aphid.md
│   └── ...
├── crops/              # 作物知识
│   ├── tomato.md
│   └── ...
└── chemicals/          # 农药知识（可选）
    └── ...
```

### 添加新知识

1. **创建知识文件**

   在 `data/knowledge/` 对应目录下创建 Markdown 文件：

   ```markdown
   # 番茄早疫病

   ## 病原
   番茄早疫病由链格孢菌引起...

   ## 症状
   叶片出现圆形病斑...

   ## 防治措施
   ### 化学防治
   - **70% 代森锰锌可湿性粉剂**
     - 用量：150-200 g/亩
     - 稀释：500-600 倍液
   ```

2. **摄取到 ChromaDB**

   ```bash
   # 增量模式（添加新文档）
   uv run python scripts/ingest_knowledge.py --path data/knowledge/ --append

   # 或重置模式（重建整个数据库）
   uv run python scripts/ingest_knowledge.py --path data/knowledge/ --reset
   ```

3. **验证摄取结果**

   ```bash
   # 检查 ChromaDB 目录
   ls -la data/chroma/

   # 运行测试查询
   uv run python -c "
   from app.services.rag_service import get_rag_service
   rag = get_rag_service()
   docs = rag.query('番茄早疫病', top_k=3)
   for i, doc in enumerate(docs, 1):
       print(f'{i}. {doc.metadata[\"source\"]}')
       print(f'   {doc.page_content[:100]}...')
   "
   ```

### 知识文件编写规范

#### 格式要求

- 使用标准 Markdown 格式
- 文件名使用小写字母和下划线：`powdery_mildew.md`
- 使用二级标题（`##`）分隔主要章节

#### 推荐章节结构

```markdown
# 病害/害虫名称

## 病原/形态特征
简要描述病原或害虫的生物学特征...

## 症状/危害特点
描述受害部位和症状表现...

## 发生规律
- 温度条件
- 湿度条件
- 传播途径

## 防治措施
### 农业防治
- 措施1
- 措施2

### 生物防治
- 措施1

### 化学防治
推荐药剂：
1. **药剂名称**
   - 用量：XX g/亩 或 ml/亩
   - 稀释倍数：XXX 倍液
   - 安全间隔期：X 天

## 预防措施
- 栽培管理建议
- 注意事项
```

#### 内容质量要求

- **准确性**: 所有防治措施必须基于官方农业指导
- **完整性**: 包含病原、症状、防治、预防四个部分
- **可操作性**: 药剂使用必须包含具体用量和稀释倍数
- **安全性**: 必须注明安全间隔期和注意事项

---

## 摄取脚本使用

### 基本用法

```bash
# 默认模式：处理 data/knowledge/ 目录
uv run python scripts/ingest_knowledge.py

# 指定路径
uv run python scripts/ingest_knowledge.py --path /path/to/knowledge/

# 增量模式：添加到现有数据库
uv run python scripts/ingest_knowledge.py --append

# 重置模式：清空并重建数据库
uv run python scripts/ingest_knowledge.py --reset

# 自定义切片参数
uv run python scripts/ingest_knowledge.py --chunk-size 1500 --overlap 300
```

### 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--path` | `data/knowledge/` | 知识文件目录 |
| `--append` | False | 增量模式，添加到现有数据库 |
| `--reset` | False | 重置模式，删除并重建数据库 |
| `--chunk-size` | 1000 | 文档切片大小（字符数） |
| `--overlap` | 200 | 切片重叠大小（字符数） |

### 切片参数优化建议

| 内容类型 | 推荐chunk_size | 推荐overlap | 说明 |
|----------|----------------|-------------|------|
| 简短病害描述 | 800 | 150 | 保持内容连贯性 |
| 详细防治指南 | 1200 | 200 | 包含完整章节 |
| 长篇综合文档 | 1500 | 300 | 减少切片数量 |

### 输出示例

```
📚 Knowledge Base Ingestion Script
==================================
Path: data/knowledge/
Mode: reset (rebuild database)
Chunk size: 1000, Overlap: 200

📄 Processing files...
  ✅ diseases/powdery_mildew.md (2.3 KB)
  ✅ diseases/late_blight.md (2.8 KB)
  ✅ crops/tomato.md (4.1 KB)

🔪 Splitting documents...
  ✅ Created 47 chunks from 3 files

📊 Creating embeddings...
  ✅ Embedded 47 chunks (took 12.3s)

💾 Storing in ChromaDB...
  ✅ Stored at: data/chroma/

✨ Done!
  Processed 3 files
  Created 47 chunks
  Time elapsed: 15.8s
  ChromaDB path: data/chroma/
```

---

## ChromaDB 管理

### 数据库位置

默认持久化目录：`data/chroma/`

可通过环境变量自定义：
```bash
export CHROMA_PERSIST_DIRECTORY="/path/to/chroma"
```

### 数据库备份

```bash
# 创建备份
tar -czf chroma_backup_$(date +%Y%m%d).tar.gz data/chroma/

# 恢复备份
tar -xzf chroma_backup_20250125.tar.gz
```

### 数据库清理

```bash
# 删除整个数据库
rm -rf data/chroma/

# 重新摄取
uv run python scripts/ingest_knowledge.py --path data/knowledge/ --reset
```

### 查看数据库统计

```python
from app.services.rag_service import get_rag_service

rag = get_rag_service()

# 获取底层 ChromaDB 实例
chroma_db = rag._get_chroma_db()

# 获取集合信息
collection = chroma_db._collection
print(f"Total documents: {collection.count()}")
```

---

## 故障排查

### 常见问题

#### 1. RAG 服务未初始化

**错误信息**:
```
RAGServiceNotInitializedError: ChromaDB not initialized at data/chroma/
```

**解决方案**:
```bash
# 运行摄取脚本初始化数据库
uv run python scripts/ingest_knowledge.py --path data/knowledge/
```

#### 2. API 密钥未配置

**错误信息**:
```
Error: OPENAI_API_KEY not found in environment variables
```

**解决方案**:
```bash
# 在 .env 文件中添加
echo "OPENAI_API_KEY=sk-..." >> .env

# 或设置环境变量
export OPENAI_API_KEY="sk-..."
```

#### 3. 摄取脚本找不到文件

**错误信息**:
```
Warning: No markdown files found in /path/to/knowledge/
```

**解决方案**:
- 检查目录路径是否正确
- 确认目录中包含 .md 或 .pdf 文件
- 使用 `ls` 命令验证文件存在

#### 4. 向量化失败

**错误信息**:
```
Error: Failed to create embeddings: OpenAI API error
```

**可能原因**:
- API 密钥无效或过期
- 网络连接问题
- API 配额用尽

**解决方案**:
```bash
# 验证 API 密钥
echo $OPENAI_API_KEY

# 测试 API 连接
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# 检查 SiliconFlow 配置（如果使用）
echo $OPENAI_BASE_URL
```

#### 5. 检索结果不相关

**症状**: 查询返回的文档与问题不相关

**解决方案**:

1. **检查知识库内容**:
   ```bash
   # 列出所有已摄取的文档
   uv run python -c "
   from app.services.rag_service import get_rag_service
   rag = get_rag_service()
   chroma_db = rag._get_chroma_db()
   collection = chroma_db._collection

   # 获取所有文档的元数据
   results = collection.get(include=['metadatas'])
   sources = set(m['source'] for m in results['metadatas'])
   for source in sources:
       print(f'  - {source}')
   "
   ```

2. **优化查询文本**:
   - 使用具体的专业术语
   - 包含作物类型：`番茄 晚疫病` 而不是 `晚疫病`
   - 尝试同义词：`叶霉病` vs `灰霉病`

3. **调整切片参数**:
   ```bash
   # 减小 chunk_size 提高精确度
   uv run python scripts/ingest_knowledge.py --chunk-size 800 --reset
   ```

#### 6. 内存不足

**症状**: 大型知识库摄取时内存溢出

**解决方案**:
```bash
# 分批摄取不同目录
uv run python scripts/ingest_knowledge.py --path data/knowledge/diseases/ --append
uv run python scripts/ingest_knowledge.py --path data/knowledge/pests/ --append
uv run python scripts/ingest_knowledge.py --path data/knowledge/crops/ --append
```

### 调试技巧

#### 启用详细日志

```bash
# 设置日志级别
export LOG_LEVEL=DEBUG

# 运行摄取脚本
uv run python scripts/ingest_knowledge.py --path data/knowledge/
```

#### 测试 RAG 查询

```python
# 创建测试脚本 test_rag.py
from app.services.rag_service import get_rag_service
import logging

logging.basicConfig(level=logging.DEBUG)

rag = get_rag_service()

# 测试查询
query = "番茄晚疫病怎么防治？"
docs = rag.query(query, top_k=3)

print(f"\n查询: {query}")
print(f"检索到 {len(docs)} 个文档:\n")

for i, doc in enumerate(docs, 1):
    print(f"{i}. 来源: {doc.metadata['source']}")
    print(f"   内容: {doc.page_content[:150]}...")
    print()
```

#### 检查嵌入质量

```bash
# 测试嵌入模型
uv run python -c "
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
load_dotenv()

embeddings = OpenAIEmbeddings()
text = '番茄晚疫病由致病疫霉引起'
vector = embeddings.embed_query(text)

print(f'向量维度: {len(vector)}')
print(f'前5个值: {vector[:5]}')
"
```

---

## 最佳实践

### 知识库维护

1. **定期更新**: 每季度审查和更新知识内容
2. **版本控制**: 使用 Git 管理知识文件
3. **审核流程**: 新内容需经农业专家审核
4. **分类管理**: 按作物、病害类型、地区组织内容

### 性能优化

1. **控制切片数量**:
   - 单次诊断通常只需要 top_k=3
   - 避免过度切片（chunk_size < 500）

2. **使用增量更新**:
   - 优先使用 `--append` 而不是 `--reset`
   - 只摄取变更的文件

3. **缓存查询结果**:
   - 相同诊断结果的报告可以缓存
   - 考虑实现报告缓存机制

### 成本控制

1. **优化嵌入模型**:
   - 考虑使用本地嵌入模型（如 BGE-M3）
   - SiliconFlow 比 OpenAI 更便宜

2. **减少 API 调用**:
   - 批量摄取而非单文件
   - 缓存常用查询的向量

3. **监控使用量**:
   ```bash
   # 查看嵌入 API 使用统计
   # （需要根据实际 API 提供商查询）
   ```

---

## 相关文档

- [报告生成指南](./report_generation.md)
- [诊断工作流程](./diagnosis_workflow.md)
- [Taxonomy 使用指南](./taxonomy_usage.md)

---

## 更新日志

- **2025-01-25**: 初始版本，支持 Markdown/PDF 知识库摄取
- 未来计划：支持图片、视频等多媒体知识
