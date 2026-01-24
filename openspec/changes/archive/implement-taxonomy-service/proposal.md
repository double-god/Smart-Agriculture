# Proposal: Implement Taxonomy Service (implement-taxonomy-service)

**Change ID**: `implement-taxonomy-service`
**Status**: Proposed
**Created**: 2026-01-22
**Author**: Claude (Full-Stack Agent Architect)

---

## 1. Problem Statement

The Smart-Agriculture system currently lacks a **centralized taxonomy service** to manage the standardized pest and disease classification defined in `data/taxonomy_standard_v1.json`.

This creates several issues:
- **Hard-coded Labels**: CV model outputs (e.g., `class_id: 3`) need manual mapping to Chinese names ("叶螨") scattered across the codebase
- **No Validation**: No runtime guarantee that CV model outputs align with the taxonomy standard
- **RAG Integration Difficulty**: Search keywords for ChromaDB retrieval are buried in JSON, requiring manual parsing
- **Maintenance Risk**: Adding new taxonomy entries requires changes in multiple files

This violates the **Taxonomy Compliance** rule from `openspec/project.md`:
> All pest/disease labels MUST align with `data/taxonomy_standard_v1.json`. AI must handle label mapping explicitly.

---

## 2. Proposed Solution

Implement a **Singleton Taxonomy Service** that:
1. **Loads** `taxonomy_standard_v1.json` at startup into Pydantic models
2. **Provides** type-safe query methods:
   - `get_by_id(id)` → Returns `TaxonomyEntry`
   - `get_by_name(name)` → Returns `TaxonomyEntry`
   - `get_search_keywords(id)` → Returns list of keywords for RAG
3. **Validates** CV model outputs against the taxonomy
4. **Injects** via FastAPI dependency injection for easy access

---

## 3. Architecture Decisions

### 3.1. Singleton Pattern
**Decision**: Use a singleton class `TaxonomyService` with module-level instance.

**Rationale**:
- JSON data is **read-only** after initialization
- Single in-memory copy reduces memory footprint
- Lazy loading: only loads when first accessed
- Thread-safe for read operations (no mutations after init)

**Trade-offs**:
- Global state (but acceptable for read-only reference data)
- Mitigation: Mark service as `@final` and document immutability

### 3.2. Pydantic Models for Validation
**Decision**: Define strict Pydantic models matching JSON structure.

**Rationale**:
- Runtime validation ensures JSON schema compliance
- Type hints enable IDE autocomplete
- Automatic error messages if JSON is malformed

**Trade-offs**:
- Slight overhead at startup for validation
- Mitigation: One-time cost, negligible compared to CV inference

### 3.3. Dependency Injection
**Decision**: Provide FastAPI dependency function `get_taxonomy_service()`.

**Rationale**:
- Easy access in API routes and Celery tasks
- Mockable for unit testing
- Follows FastAPI best practices

---

## 4. Impact Assessment

### 4.1. Affected Components
- **New Files Created**:
  - `app/models/taxonomy.py` (Pydantic models)
  - `app/services/taxonomy_service.py` (Singleton service)
  - `app/core/deps.py` (Dependency injection utilities)
  - `tests/services/test_taxonomy.py` (Unit tests)

- **Modified Files**:
  - None (pure addition)

### 4.2. Breaking Changes
- **None** (this is a new service, existing code unaffected)

### 4.3. Migration Path
- No migration needed (new capability)

---

## 5. Success Criteria

The implementation is considered successful when:

1. [ ] TaxonomyService loads JSON without errors at startup
2. [ ] `get_by_id(3)` returns correct entry for "叶螨" (spider_mite)
3. [ ] `get_by_name("蚜虫类")` returns entry with id=1
4. [ ] `get_search_keywords(3)` returns `["红蜘蛛", "二斑叶螨"]`
5. [ ] Unit tests achieve >90% coverage
6. [ ] Dependency injection works in FastAPI routes
7. [ ] Invalid ID raises `TaxonomyNotFoundError`

---

## 6. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| JSON file missing at runtime | High | Fail-fast at startup with clear error message |
| JSON schema changes break code | Medium | Pydantic validation catches mismatch; add unit tests |
| Singleton initialization race condition | Low | Use module-level `__init__` guard (Python GIL protection) |
| Performance overhead of service calls | Low | In-memory dict lookup is O(1), negligible |

---

## 7. Open Questions

None at this time. The scope is well-defined as a foundational service for CV-RAG integration.

---

## 8. Related Specifications

See `openspec/changes/implement-taxonomy-service/specs/taxonomy/spec.md` for detailed taxonomy data model requirements.
