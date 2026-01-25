"""
LangChain implementations for agricultural diagnosis workflows.

This module contains Chain implementations for generating plant disease
and pest reports using dynamic template switching based on CV results.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_openai import ChatOpenAI

from app.core.templates import (
    get_report_template,
    TEMPLATE_TYPE_DISEASE,
    TEMPLATE_TYPE_PEST,
)

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Configuration
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
DEFAULT_TIMEOUT = 30  # seconds


class LLMError(Exception):
    """Base exception for LLM-related errors."""

    pass


class ReportTimeoutError(LLMError):
    """Raised when LLM call times out."""

    pass


class GenerateReport:
    """
    A LangChain-based report generator that dynamically switches between
    disease and pest templates based on CV classification results.

    Architecture:
        1. Receives CV result (diagnosis type, name, confidence)
        2. Receives RAG context (retrieved documents)
        3. Routes to appropriate template (Disease vs Pest)
        4. Generates structured report via LLM
    """

    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        temperature: float = 0.3,
    ):
        """
        Initialize the report generation chain.

        Args:
            model_name: OpenAI model identifier
            temperature: LLM temperature (lower = more factual)
        """
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
        )
        self.output_parser = StrOutputParser()

    def _format_context(self, documents: List[Document]) -> str:
        """
        Format retrieved RAG documents into a context string.

        Args:
            documents: List of LangChain Document objects

        Returns:
            Formatted context string
        """
        if not documents:
            return "未检索到相关上下文信息。"

        formatted_sections = []
        for i, doc in enumerate(documents, 1):
            formatted_sections.append(
                f"【上下文片段 {i}】\n{doc.page_content}\n"
            )

        return "\n".join(formatted_sections)

    def _prepare_template_inputs(
        self,
        diagnosis_type: str,
        diagnosis_name: str,
        diagnosis_en_name: Optional[str],
        documents: List[Document],
    ) -> Dict[str, Any]:
        """
        Prepare inputs for the selected template.

        Args:
            diagnosis_type: "Disease" or "Pest"
            diagnosis_name: Chinese common name
            diagnosis_en_name: English/scientific name
            documents: RAG retrieved documents

        Returns:
            Dictionary of template variables
        """
        base_inputs = {
            "diagnosis_name": diagnosis_name,
            "diagnosis_en_name": diagnosis_en_name or "",
            "context": self._format_context(documents),
        }

        # Type-specific defaults
        if diagnosis_type == TEMPLATE_TYPE_DISEASE:
            base_inputs.update({
                "pathogen_info": "[请从上下文中提取]",
                "symptoms": "[请从上下文中提取]",
                "ecology": "[请从上下文中提取]",
                "control_measures": "[请从上下文中提取，分点列出]",
            })
        elif diagnosis_type == TEMPLATE_TYPE_PEST:
            base_inputs.update({
                "general_intro": "[请从上下文中提取]",
                "species_list": "[请列出学名和英名]",
                "habits_and_damage": "[请从上下文中提取]",
                "biological_control": "[请从上下文中提取]",
                "chemical_control": "[请从上下文中提取，含药剂、浓度、安全间隔期]",
            })

        return base_inputs

    def generate(
        self,
        diagnosis_type: str,
        diagnosis_name: str,
        diagnosis_en_name: Optional[str],
        documents: List[Document],
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate a diagnostic report based on CV results and RAG context.

        Args:
            diagnosis_type: Either "Disease" or "Pest"
            diagnosis_name: Standard Chinese name from taxonomy
            diagnosis_en_name: English or scientific name
            documents: Retrieved documents from ChromaDB
            additional_context: Optional extra data (e.g., crop type, confidence)

        Returns:
            Generated report text in Markdown format

        Raises:
            ValueError: If diagnosis_type is not "Disease" or "Pest"
        """
        # Route to appropriate template
        template_str = get_report_template(diagnosis_type)

        # Prepare template inputs
        template_inputs = self._prepare_template_inputs(
            diagnosis_type=diagnosis_type,
            diagnosis_name=diagnosis_name,
            diagnosis_en_name=diagnosis_en_name,
            documents=documents,
        )

        # Merge additional context if provided
        if additional_context:
            template_inputs.update(additional_context)

        # Construct the prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一名农业专家，擅长植物病虫害诊断和防治建议。"),
            ("human", template_str),
        ])

        # Create and invoke the chain
        chain = prompt | self.llm | self.output_parser

        try:
            report = chain.invoke(template_inputs)
            return report
        except Exception as e:
            raise RuntimeError(f"Report generation failed: {str(e)}") from e

    async def agenerate(
        self,
        diagnosis_type: str,
        diagnosis_name: str,
        diagnosis_en_name: Optional[str],
        documents: List[Document],
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Async version of generate().

        Useful when calling from async Celery tasks or FastAPI endpoints.
        """
        # Route to appropriate template
        template_str = get_report_template(diagnosis_type)

        # Prepare template inputs
        template_inputs = self._prepare_template_inputs(
            diagnosis_type=diagnosis_type,
            diagnosis_name=diagnosis_name,
            diagnosis_en_name=diagnosis_en_name,
            documents=documents,
        )

        # Merge additional context if provided
        if additional_context:
            template_inputs.update(additional_context)

        # Construct the prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一名农业专家，擅长植物病虫害诊断和防治建议。"),
            ("human", template_str),
        ])

        # Create and invoke the chain (async)
        chain = prompt | self.llm | self.output_parser

        try:
            report = await chain.ainvoke(template_inputs)
            return report
        except Exception as e:
            raise RuntimeError(f"Async report generation failed: {str(e)}") from e


# Convenience factory function
def create_report_chain(
    model_name: str = "gpt-4o-mini",
    temperature: float = 0.3,
) -> GenerateReport:
    """
    Factory function to create a pre-configured GenerateReport instance.

    Args:
        model_name: OpenAI model to use
        temperature: LLM sampling temperature

    Returns:
        Configured GenerateReport instance
    """
    return GenerateReport(model_name=model_name, temperature=temperature)


# =============================================================================
# New simplified report generation function for RAG integration
# =============================================================================

# Prompt template for diagnosis report
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
2. **防治措施**: 包括农业防治、生物防治、化学防治
   （如有推荐药剂，请列出药剂名称、用量、稀释倍数、安全间隔期）
3. **预防措施**: 种植前预防、栽培管理建议、注意事项

请使用专业但易懂的语言，确保农户能够理解并实施。

## 诊断报告
"""

# Global cached LLM instance to enable connection reuse
_CACHED_LLM: Optional[ChatOpenAI] = None


def _get_llm(timeout: int = DEFAULT_TIMEOUT) -> ChatOpenAI:
    """
    Initialize or retrieve cached OpenAI Chat LLM instance.

    Uses a cached instance if available and timeout matches default,
    otherwise creates a new instance.

    Args:
        timeout: Request timeout in seconds

    Returns:
        ChatOpenAI instance configured for SiliconFlow API
    """
    global _CACHED_LLM

    # Return cached instance if using default timeout
    if _CACHED_LLM is not None and timeout == DEFAULT_TIMEOUT:
        return _CACHED_LLM

    if OPENAI_BASE_URL:
        logger.debug(f"Using custom base URL: {OPENAI_BASE_URL}")
        logger.debug(f"Using chat model: {OPENAI_CHAT_MODEL}")
        llm = ChatOpenAI(
            model=OPENAI_CHAT_MODEL,
            base_url=OPENAI_BASE_URL,
            temperature=0.7,
            timeout=timeout,
        )
    else:
        llm = ChatOpenAI(
            model=OPENAI_CHAT_MODEL,
            temperature=0.7,
            timeout=timeout,
        )

    # Cache the instance if using default settings
    if timeout == DEFAULT_TIMEOUT:
        _CACHED_LLM = llm

    return llm


def _format_contexts(contexts: List[Document]) -> str:
    """
    Format retrieved documents into a readable context string.

    Args:
        contexts: List of retrieved Document objects

    Returns:
        Formatted context string for prompt
    """
    if not contexts:
        return "**未找到相关资料**。以下报告基于通用知识生成，建议参考专业农业资料确认。"

    formatted_sections = []
    for i, doc in enumerate(contexts, 1):
        source = doc.metadata.get("source", "未知来源")
        content = doc.page_content.strip()
        formatted_sections.append(f"### 资料 {i}: {source}\n\n{content}\n")

    return "\n".join(formatted_sections)


def _get_confidence_warning(confidence: float) -> str:
    """
    Generate warning message based on confidence level.

    Args:
        confidence: Confidence score (0.0 to 1.0)

    Returns:
        Warning message string
    """
    if confidence < 0.5:
        return ("⚠️ **警告**: 置信度很低（<50%），诊断结果可能不准确，"
                "强烈建议重新拍照或咨询农业专家。")
    elif confidence < 0.7:
        return "⚠️ **提示**: 置信度较低（<70%），建议重新拍照确认诊断结果。"
    else:
        return ""


def generate_diagnosis_report(
    diagnosis_name: str,
    crop_type: str,
    confidence: float,
    contexts: List[Document],
    llm: Optional[ChatOpenAI] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """
    Generate a comprehensive diagnosis report using LLM.

    This function retrieves relevant agricultural knowledge and uses an LLM
    to generate a structured, actionable diagnosis report for farmers.

    Args:
        diagnosis_name: Name of the diagnosed disease (e.g., "番茄晚疫病")
        crop_type: Type of crop (e.g., "番茄")
        confidence: Confidence score (0.0 to 1.0)
        contexts: List of relevant documents retrieved from knowledge base
        llm: Optional pre-configured LLM instance (for testing/customization)
        timeout: Request timeout in seconds (default: 30)

    Returns:
        Generated diagnosis report in Markdown format

    Raises:
        ReportTimeoutError: If LLM call exceeds timeout
        LLMError: If LLM API call fails for any reason

    Example:
        >>> from app.worker.chains import generate_diagnosis_report
        >>> report = generate_diagnosis_report(
        ...     diagnosis_name="番茄晚疫病",
        ...     crop_type="番茄",
        ...     confidence=0.92,
        ...     contexts=relevant_docs,
        ... )
        >>> print(report)
    """
    logger.info(f"Generating report for {diagnosis_name} (confidence={confidence:.2f})")

    # Validate inputs
    if not diagnosis_name or not diagnosis_name.strip():
        raise ValueError("diagnosis_name cannot be empty")

    if not crop_type or not crop_type.strip():
        raise ValueError("crop_type cannot be empty")

    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")

    try:
        # Initialize LLM
        if llm is None:
            llm = _get_llm(timeout=timeout)

        # Format contexts
        context_section = _format_contexts(contexts)

        # Generate confidence warning
        confidence_warning = _get_confidence_warning(confidence)

        # Create prompt
        prompt_template = PromptTemplate(
            template=SIMPLIFIED_REPORT_TEMPLATE,
            input_variables=[
                "crop_type",
                "diagnosis_name",
                "confidence",
                "confidence_warning",
                "context_section",
            ],
        )

        # Build prompt inputs
        prompt_inputs = {
            "crop_type": crop_type,
            "diagnosis_name": diagnosis_name,
            "confidence": confidence,
            "confidence_warning": confidence_warning,
            "context_section": context_section,
        }

        # Generate report using LLM chain
        logger.info("Invoking LLM for report generation...")
        chain = prompt_template | llm | StrOutputParser()
        report = chain.invoke(prompt_inputs)

        logger.info(f"Report generated successfully ({len(report)} chars)")
        return report

    except ReportTimeoutError as e:
        logger.error(f"LLM call timed out after {timeout}s: {str(e)}")
        raise

    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)

        # Handle timeout errors
        if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            logger.error(f"LLM timeout: {error_msg}")
            raise ReportTimeoutError(f"LLM call timed out: {error_msg}") from e

        # Handle rate limit errors
        if "rate limit" in error_msg.lower() or "429" in error_msg:
            logger.error(f"OpenAI rate limit exceeded: {error_msg}")
            raise LLMError(f"API rate limit exceeded: {error_msg}") from e

        # Handle authentication errors
        if "authentication" in error_msg.lower() or "401" in error_msg:
            logger.error(f"OpenAI authentication failed: {error_msg}")
            raise LLMError(f"API authentication failed: {error_msg}") from e

        # Generic error
        logger.error(f"Failed to generate report: {error_type}: {error_msg}")
        raise LLMError(f"Report generation failed: {error_msg}") from e


async def generate_diagnosis_report_async(
    diagnosis_name: str,
    crop_type: str,
    confidence: float,
    contexts: List[Document],
    llm: Optional[ChatOpenAI] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """
    Async version of generate_diagnosis_report().

    This function provides async/await interface for LLM-based report generation,
    enabling efficient concurrency in Celery workers when processing multiple requests.

    Args:
        diagnosis_name: Name of the diagnosed disease (e.g., "番茄晚疫病")
        crop_type: Type of crop (e.g., "番茄")
        confidence: Confidence score (0.0 to 1.0)
        contexts: List of relevant documents retrieved from knowledge base
        llm: Optional pre-configured LLM instance (for testing/customization)
        timeout: Request timeout in seconds (default: 30)

    Returns:
        Generated diagnosis report in Markdown format

    Raises:
        ReportTimeoutError: If LLM call exceeds timeout
        LLMError: If LLM API call fails for any reason

    Example:
        >>> import asyncio
        >>> from app.worker.chains import generate_diagnosis_report_async
        >>> report = asyncio.run(generate_diagnosis_report_async(
        ...     diagnosis_name="番茄晚疫病",
        ...     crop_type="番茄",
        ...     confidence=0.92,
        ...     contexts=relevant_docs,
        ... ))
        >>> print(report)
    """
    logger.info(f"Generating async report for {diagnosis_name} (confidence={confidence:.2f})")

    # Validate inputs
    if not diagnosis_name or not diagnosis_name.strip():
        raise ValueError("diagnosis_name cannot be empty")

    if not crop_type or not crop_type.strip():
        raise ValueError("crop_type cannot be empty")

    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")

    try:
        # Initialize LLM
        if llm is None:
            llm = _get_llm(timeout=timeout)

        # Format contexts
        context_section = _format_contexts(contexts)

        # Generate confidence warning
        confidence_warning = _get_confidence_warning(confidence)

        # Create prompt
        prompt_template = PromptTemplate(
            template=SIMPLIFIED_REPORT_TEMPLATE,
            input_variables=[
                "crop_type",
                "diagnosis_name",
                "confidence",
                "confidence_warning",
                "context_section",
            ],
        )

        # Build prompt inputs
        prompt_inputs = {
            "crop_type": crop_type,
            "diagnosis_name": diagnosis_name,
            "confidence": confidence,
            "confidence_warning": confidence_warning,
            "context_section": context_section,
        }

        # Generate report using async LLM chain
        logger.info("Invoking LLM for async report generation...")
        chain = prompt_template | llm | StrOutputParser()
        report = await chain.ainvoke(prompt_inputs)

        logger.info(f"Async report generated successfully ({len(report)} chars)")
        return report

    except ReportTimeoutError as e:
        logger.error(f"Async LLM call timed out after {timeout}s: {str(e)}")
        raise

    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)

        # Handle timeout errors
        if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            logger.error(f"Async LLM timeout: {error_msg}")
            raise ReportTimeoutError(f"LLM call timed out: {error_msg}") from e

        # Handle rate limit errors
        if "rate limit" in error_msg.lower() or "429" in error_msg:
            logger.error(f"OpenAI rate limit exceeded: {error_msg}")
            raise LLMError(f"API rate limit exceeded: {error_msg}") from e

        # Handle authentication errors
        if "authentication" in error_msg.lower() or "401" in error_msg:
            logger.error(f"OpenAI authentication failed: {error_msg}")
            raise LLMError(f"API authentication failed: {error_msg}") from e

        # Generic error
        logger.error(f"Failed to generate async report: {error_type}: {error_msg}")
        raise LLMError(f"Report generation failed: {error_msg}") from e
