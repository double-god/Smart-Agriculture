"""
Prompt Templates for Plant Disease and Pest Report Generation

This module defines structured prompt templates for generating agricultural
diagnosis reports based on CV classification results (Disease vs Pest).
"""

# Template 1: Disease Report (Concise Style)
DISEASE_REPORT_TEMPLATE = """你是一名植物病理学专家。请基于以下检索到的上下文（Context），严格按照下述格式生成诊断报告。

---
**诊断结果**：{diagnosis_name} {diagnosis_en_name}

**病原**：{pathogen_info}
**病征**：{symptoms}
**发生生态**：{ecology}
**防治**：
{control_measures}
---

**注意**：
1. "防治"部分必须分点（如 a, b...）。
2. 化学药剂必须包含浓度倍数（如 500倍）。
3. 如果上下文没有提到某项信息（如病原），请标注"资料不足"。
"""

# Template 2: Pest Report (Encyclopedic Style)
PEST_REPORT_TEMPLATE = """你是一名农业昆虫学专家。请基于以下检索到的上下文（Context），严格按照下述格式生成详细报告。

---
**诊断结果**：**{diagnosis_name}**

{general_intro}

**主要种类**：
{species_list}

**（一）生活习性与危害状**
{habits_and_damage}

**（二）防治方法**
1. **生物防治**：{biological_control}
2. **药剂防治**：{chemical_control}
---

**注意**：
1. "主要种类"部分请列出学名和英名（如果有）。
2. "药剂防治"部分必须列出具体的药剂名称、浓度（倍数）和安全间隔期建议。
3. 保持排版整洁，使用 Markdown 加粗关键术语。
"""


def get_report_template(diagnosis_type: str) -> str:
    """
    Select the appropriate report template based on diagnosis type.

    Args:
        diagnosis_type: Either "Disease" or "Pest" (case-insensitive)

    Returns:
        The corresponding prompt template string

    Raises:
        ValueError: If diagnosis_type is not recognized
    """
    if diagnosis_type.lower() == "disease":
        return DISEASE_REPORT_TEMPLATE
    elif diagnosis_type.lower() == "pest":
        return PEST_REPORT_TEMPLATE
    else:
        raise ValueError(
            f"Unknown diagnosis type: '{diagnosis_type}'. "
            f"Expected 'Disease' or 'Pest'."
        )


# Template type constants for type safety
TEMPLATE_TYPE_DISEASE = "Disease"
TEMPLATE_TYPE_PEST = "Pest"
