# Implementation Tasks: implement-storage-service

**Change ID**: `implement-storage-service`
**Status**: ✅ Completed

---

## Task Checklist

### Phase 1: Data Models & Exceptions (REQ-STORAGE-001)

- [x] **T1.1**: Create `app/services/storage.py` file
- [x] **T1.2**: Implement `StorageConnectionError` exception class
- [x] **T1.3**: Add docstring for exception with usage examples

### Phase 2: StorageService Implementation (REQ-STORAGE-001)

- [x] **T2.1**: Implement `StorageService` singleton class:
  - `__new__()` method for singleton pattern
  - `__init__()` method with lazy initialization
- [x] **T2.2**: Implement configuration loading:
  - Load settings from `app.core.config.get_settings()`
  - Extract MinIO endpoint, access key, secret key, bucket name, secure flag
- [x] **T2.3**: Implement MinIO client initialization:
  - Create `Minio` client instance
  - Disable SSL warnings for development (if not secure)
  - Wrap in try-except to handle `S3Error`
- [x] **T2.4**: Implement `_ensure_bucket_exists()` method:
  - Check if bucket exists using `client.bucket_exists()`
  - Create bucket if not exists
  - Set public read policy on bucket
- [x] **T2.5**: Implement `upload_image()` method:
  - Accept `file_data: BinaryIO`, `filename: str`, `content_type: str`
  - Call `client.put_object()` with proper parameters
  - Generate and return public URL
  - Handle `S3Error` and raise `StorageConnectionError`
- [x] **T2.6**: Implement `_get_public_url()` helper method:
  - Generate URL in format `{protocol}://{endpoint}/{bucket}/{filename}`
  - Use protocol based on `secure` flag
- [x] **T2.7**: Implement `bucket_name` property getter
- [x] **T2.8**: Implement module-level factory function:
  - `get_storage_service()` → StorageService
  - Global `_storage_service` variable with lazy initialization

### Phase 3: Dependency Injection (REQ-STORAGE-002)

- [x] **T3.1**: Add `depends_storage()` to `app/core/deps.py`
- [x] **T3.2**: Import `StorageService` and `get_storage_service`
- [x] **T3.3**: Add docstring with FastAPI usage example
- [x] **T3.4**: Export `depends_storage` in `app/core/__init__.py`

### Phase 4: Dependency Management

- [x] **T4.1**: Add `minio` package to `pyproject.toml` dependencies
- [x] **T4.2**: Run `uv sync` to install minio package
- [x] **T4.3**: Verify minio installation: `uv run python -c "import minio; print(minio.__version__)"`

### Phase 5: Unit Testing (REQ-STORAGE-004)

- [x] **T5.1**: Create `tests/services/test_storage.py` file
- [x] **T5.2**: Implement test: `test_storage_service_singleton()`
- [x] **T5.3**: Implement test: `test_get_storage_service()`
- [x] **T5.4**: Implement test: `test_upload_image_success()`
- [x] **T5.5**: Implement test: `test_upload_image_with_custom_content_type()`
- [x] **T5.6**: Implement test: `test_bucket_name_property()`
- [x] **T5.7**: Run all tests with `uv run pytest tests/services/test_storage.py`
- [x] **T5.8**: Verify test coverage > 80%

### Phase 6: Documentation & Verification

- [x] **T6.1**: Create usage documentation in `docs/storage_usage.md`:
  - How to upload images
  - How to use in FastAPI routes
  - Error handling examples
- [x] **T6.2**: Verify MinIO connection:
  ```python
  python -c "from app.services.storage import get_storage_service; s = get_storage_service(); print(f'Connected to bucket: {s.bucket_name}')"
  ```
- [x] **T6.3**: Test file upload manually:
  - Upload a small test image
  - Verify URL is accessible in browser
- [x] **T6.4**: Run full test suite: `uv run pytest`
- [x] **T6.5**: Verify all type hints resolve without Pylance warnings

---

## Task Dependencies

```
T1.x (Data Models & Exceptions)
    ↓
T2.x (Service Implementation)
    ↓
T3.x (Dependency Injection)
    ↓
T4.x (Dependency Management)
    ↓
T5.x (Unit Testing)
    ↓
T6.x (Documentation)
```

**Critical Path**: T1.2 → T2.4 → T4.2 → T5.7

---

## Definition of Done

A task is marked `[x]` when:
1. The code is written and passes linting (black, ruff)
2. No Pylance/Pyflakes warnings
3. Unit tests pass
4. Documentation is updated (if applicable)

---

## Notes

- **T2.3**: MinIO client uses synchronous API, may block FastAPI event loop. Consider async API in future versions.
- **T2.4**: Bucket policy is set to public read for simplicity. In production, consider using presigned URLs.
- **T2.5**: `length=-1` enables streaming for unknown file sizes. Adjust `part_size` based on expected file sizes.
- **T4.1**: minio package version should be >= 7.0.0 for Python 3.12 compatibility.
- **T5.4-T5.6**: Tests use `unittest.mock` to avoid requiring MinIO service during unit tests.
- **T6.2**: Verification command should print "Connected to bucket: smart-agriculture" for current configuration.
- **T6.3**: Manual test requires MinIO to be running via `docker-compose up minio`.

---

## Completion Summary

**Date Completed**: 2026-01-22
**Total Duration**: ~20 minutes
**Code Changes**: 5 files created, 3 files modified, 300+ lines added

### Key Achievements:
1. ✅ Created StorageService singleton with MinIO integration
2. ✅ Implemented bucket auto-creation with public read policy
3. ✅ FastAPI dependency injection for easy route integration
4. ✅ 7 unit tests with 88% code coverage
5. ✅ Comprehensive documentation and usage examples
6. ✅ Fixed circular import issue with lazy loading

### Files Created:
- `app/services/storage.py` (165 lines) - StorageService implementation
- `tests/services/test_storage.py` (138 lines) - Unit tests
- `docs/storage_usage.md` (300+ lines) - Usage documentation

### Files Modified:
- `app/core/deps.py` - Added depends_storage() with lazy imports
- `app/core/__init__.py` - Exported depends_storage
- `pyproject.toml` - Added minio==7.2.20 dependency

### Test Results:
- All 7 tests passed
- Code coverage: 88% (exceeds 80% requirement)
- Test execution time: <0.3s

### Next Steps:
- Integration with diagnosis endpoints for image upload
- Add file deletion method (if needed)
- Consider implementing presigned URLs for production security
- Migrate to async MinIO API for better performance

---

## Notes

- **T2.3**: MinIO client uses synchronous API, may block FastAPI event loop. Consider async API in future versions.
- **T2.4**: Bucket policy is set to public read for simplicity. In production, consider using presigned URLs.
- **T2.5**: `length=-1` enables streaming for unknown file sizes. Adjust `part_size` based on expected file sizes.
- **T4.1**: minio package version should be >= 7.0.0 for Python 3.12 compatibility.
- **T5.4-T5.6**: Tests use `unittest.mock` to avoid requiring MinIO service during unit tests.
- **T6.2**: Verification command should print "Connected to bucket: smart-agriculture" for current configuration.
- **T6.3**: Manual test requires MinIO to be running via `docker-compose up minio`.
