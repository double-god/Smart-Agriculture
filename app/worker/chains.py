"""
LangChain implementations for agricultural diagnosis workflows.

This module contains Chain implementations for generating plant disease
and pest reports using dynamic template switching based on CV results.
"""

from typing import Any, Dict, List, Optional
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI

from app.core.templates import (
    get_report_template,
    TEMPLATE_TYPE_DISEASE,
    TEMPLATE_TYPE_PEST,
)


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
