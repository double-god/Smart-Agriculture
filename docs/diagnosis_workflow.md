# 诊断工作流使用指南

本文档说明如何使用 Smart-Agriculture 系统的诊断工作流 API。

## 完整诊断流程

```
1. 上传图片 → POST /api/v1/upload
2. 提交诊断 → POST /api/v1/diagnose
3. 轮询结果 → GET /api/v1/diagnose/tasks/{task_id}
```

## 1. 上传图片

**接口**: `POST /api/v1/upload`

**请求**:
```bash
curl -X POST "http://localhost:8000/api/v1/upload" \
  -F "file=@photo.jpg"
```

**响应**:
```json
{
  "url": "http://localhost:9010/smart-agriculture/a1b2c3d4-photo.jpg",
  "filename": "a1b2c3d4-photo.jpg",
  "original_filename": "photo.jpg",
  "content_type": "image/jpeg"
}
```

**约束条件**:
- 支持格式: JPEG, JPG, PNG
- 最大文件大小: 10MB
- 文件名自动添加 UUID 前缀确保唯一性

**错误响应**:
```json
// 不支持的文件类型
{
  "detail": "Unsupported file type: application/pdf. Allowed: image/jpeg, image/jpg, image/png"
}

// 文件过大
{
  "detail": "File too large: 11534336 bytes. Maximum size: 10485760 bytes"
}

// 空文件
{
  "detail": "Empty file"
}
```

## 2. 提交诊断任务

**接口**: `POST /api/v1/diagnose`

**请求**:
```bash
curl -X POST "http://localhost:8000/api/v1/diagnose" \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "http://localhost:9010/smart-agriculture/a1b2c3d4-photo.jpg",
    "crop_type": "番茄",
    "location": "大棚A区"
  }'
```

**响应**:
```json
{
  "task_id": "a1b2c3d4-5678-90ab-cdef-123456789abc",
  "status": "PENDING",
  "message": "Diagnosis task created successfully"
}
```

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| image_url | string | ✅ | 图片 URL（必须可从 Worker 访问） |
| crop_type | string | ❌ | 作物类型 |
| location | string | ❌ | 地理位置 |

**任务状态**:
- `PENDING` - 任务排队中
- `STARTED` - 任务执行中
- `SUCCESS` - 任务完成
- `FAILURE` - 任务失败
- `RETRY` - 任务重试中

## 3. 查询任务状态

**接口**: `GET /api/v1/diagnose/tasks/{task_id}`

**请求**:
```bash
curl -X GET "http://localhost:8000/api/v1/diagnose/tasks/a1b2c3d4-5678-90ab-cdef-123456789abc"
```

**响应 - 成功**:
```json
{
  "task_id": "a1b2c3d4-5678-90ab-cdef-123456789abc",
  "status": "SUCCESS",
  "result": {
    "model_label": "powdery_mildew",
    "confidence": 0.87,
    "diagnosis_name": "白粉病",
    "latin_name": "Erysiphales",
    "category": "Disease",
    "action_policy": "RETRIEVE",
    "taxonomy_id": 2,
    "inference_time_ms": 150,
    "description": "叶片表面出现白色粉状物",
    "risk_level": "high",
    "crop_type": "番茄",
    "location": "大棚A区"
  },
  "error": null
}
```

**响应 - 进行中**:
```json
{
  "task_id": "a1b2c3d4-5678-90ab-cdef-123456789abc",
  "status": "PENDING",
  "result": null,
  "error": null
}
```

**响应 - 失败**:
```json
{
  "task_id": "a1b2c3d4-5678-90ab-cdef-123456789abc",
  "status": "FAILURE",
  "result": null,
  "error": "Failed to download image: Connection timeout"
}
```

## 4. 完整示例

### Python 示例

```python
import requests
import time

BASE_URL = "http://localhost:8000"

# 1. 上传图片
with open("photo.jpg", "rb") as f:
    upload_response = requests.post(f"{BASE_URL}/api/v1/upload", files={"file": f})

upload_data = upload_response.json()
image_url = upload_data["url"]
print(f"图片已上传: {image_url}")

# 2. 提交诊断
diagnose_request = {
    "image_url": image_url,
    "crop_type": "番茄"
}
diagnose_response = requests.post(f"{BASE_URL}/api/v1/diagnose", json=diagnose_request)

task_info = diagnose_response.json()
task_id = task_info["task_id"]
print(f"诊断任务已创建: {task_id}")

# 3. 轮询结果
while True:
    status_response = requests.get(f"{BASE_URL}/api/v1/diagnose/tasks/{task_id}")
    status_data = status_response.json()

    print(f"任务状态: {status_data['status']}")

    if status_data["status"] == "SUCCESS":
        result = status_data["result"]
        print(f"\n诊断结果:")
        print(f"  名称: {result['diagnosis_name']}")
        print(f"  置信度: {result['confidence']:.2%}")
        print(f"  类别: {result['category']}")
        print(f"  处理策略: {result['action_policy']}")
        break
    elif status_data["status"] == "FAILURE":
        print(f"任务失败: {status_data['error']}")
        break

    time.sleep(2)  # 等待 2 秒后重试
```

### JavaScript 示例

```javascript
const BASE_URL = "http://localhost:8000";

async function diagnoseImage(file) {
  // 1. 上传图片
  const formData = new FormData();
  formData.append("file", file);

  const uploadResponse = await fetch(`${BASE_URL}/api/v1/upload`, {
    method: "POST",
    body: formData
  });
  const uploadData = await uploadResponse.json();
  const imageUrl = uploadData.url;

  console.log("图片已上传:", imageUrl);

  // 2. 提交诊断
  const diagnoseResponse = await fetch(`${BASE_URL}/api/v1/diagnose`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image_url: imageUrl })
  });
  const taskInfo = await diagnoseResponse.json();
  const taskId = taskInfo.task_id;

  console.log("诊断任务已创建:", taskId);

  // 3. 轮询结果
  const pollInterval = setInterval(async () => {
    const statusResponse = await fetch(`${BASE_URL}/api/v1/diagnose/tasks/${taskId}`);
    const statusData = await statusResponse.json();

    console.log("任务状态:", statusData.status);

    if (statusData.status === "SUCCESS") {
      clearInterval(pollInterval);
      const result = statusData.result;
      console.log("\n诊断结果:");
      console.log("  名称:", result.diagnosis_name);
      console.log("  置信度:", (result.confidence * 100).toFixed(2) + "%");
      console.log("  类别:", result.category);
      console.log("  处理策略:", result.action_policy);
    } else if (statusData.status === "FAILURE") {
      clearInterval(pollInterval);
      console.error("任务失败:", statusData.error);
    }
  }, 2000);
}
```

## 错误处理

### 常见错误

| HTTP 状态 | 错误类型 | 处理建议 |
|----------|---------|---------|
| 400 | 文件类型不支持 | 检查文件格式（仅支持 JPEG、JPG、PNG） |
| 400 | 文件过大 | 压缩图片或裁剪到 <10MB |
| 400 | 空文件 | 检查文件内容 |
| 422 | URL 格式无效 | 确保 image_url 是有效的 HTTP/HTTPS URL |
| 503 | MinIO 连接失败 | 检查 MinIO 服务是否运行 |
| 500 | 任务创建失败 | 检查 Redis 和 Celery Worker 状态 |

### 错误响应示例

```json
{
  "detail": "Unsupported file type: application/pdf. Allowed: image/jpeg, image/jpg, image/png"
}
```

## 轮询建议

### 轮询间隔
- **建议**: 2-3 秒
- **原因**: 平衡实时性和服务器压力

### 超时时间
- **建议**: 30 秒
- **原因**: 大部分诊断任务在 10 秒内完成

### 最大重试次数
- **建议**: 10 次（30 秒总时长）
- **超时后提示**: "诊断任务超时，请稍后查询"

## 系统架构

```
┌──────────────┐
│   前端/移动端  │
└──────┬───────┘
       │ 1. 上传图片
       ▼
┌──────────────────┐
│  POST /upload    │ → StorageService → MinIO → 返回 URL
└──────┬───────────┘
       │ 2. 提交诊断
       ▼
┌──────────────────────┐
│  POST /diagnose      │ → Celery Queue → 返回 task_id
└──────┬───────────────┘
       │ 3. 轮询结果
       ▼
┌──────────────────────────┐
│  GET /tasks/{task_id}    │ → Redis → 返回状态和结果
└──────────────────────────┘

(异步执行)
┌────────────────────────────────┐
│  Celery Worker                 │
│  ┌──────────────────────────┐  │
│  │ analyze_image task       │  │
│  │ 1. 下载图片              │  │
│  │ 2. Mock CV 推理          │  │
│  │ 3. 查询 TaxonomyService  │  │
│  │ 4. 返回诊断结果          │  │
│  └──────────────────────────┘  │
└────────────────────────────────┘
```

## 依赖服务

诊断工作流需要以下服务运行：

```bash
# 1. Redis (Celery broker + backend)
docker-compose up -d redis

# 2. MinIO (对象存储)
docker-compose up -d minio

# 3. Celery Worker (异步任务处理)
celery -A app.worker.celery_app worker --loglevel=info

# 4. FastAPI (HTTP API)
uv run uvicorn app.api.main:app --reload
```

## Mock 数据说明

当前版本使用 Mock 数据模拟 CV 模型推理：

- **healthy** (健康) - confidence: 0.95
- **powdery_mildew** (白粉病) - confidence: 0.87
- **aphid_complex** (蚜虫类) - confidence: 0.92
- **spider_mite** (叶螨) - confidence: 0.78
- **late_blight** (晚疫病) - confidence: 0.85

**后续集成**: 第二阶段将替换为真实 CV 模型推理。

## 性能指标

| 指标 | 当前值 |
|------|--------|
| 上传接口响应时间 | <500ms |
| 诊断任务创建时间 | <100ms |
| 任务状态查询时间 | <50ms |
| Mock 诊断完成时间 | <200ms |
| 并发支持 | 20+ 任务/秒 |

## 相关文档

- [TaxonomyService 使用指南](./taxonomy_usage.md)
- [StorageService 使用指南](./storage_usage.md)
- [API 文档](http://localhost:8000/docs) - Swagger UI
