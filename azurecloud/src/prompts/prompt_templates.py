"""
Prompt Templates Library for Enterprise Copilot
Contains all system prompts, intent classification, query rewriting, and generation templates.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class IntentType(str, Enum):
    """Supported query intents."""
    QA = "qa"
    SUMMARIZE = "summarize"
    COMPARE = "compare"
    PROCEDURAL = "procedural"
    CLARIFY = "clarify"
    TRANSLATE = "translate"
    OUT_OF_SCOPE = "out_of_scope"


@dataclass
class PromptTemplate:
    """A prompt template with placeholders."""
    name: str
    template: str
    description: str
    variables: list[str]

    def format(self, **kwargs) -> str:
        """Format template with provided variables."""
        return self.template.format(**kwargs)


# =============================================================================
# SYSTEM PROMPTS
# =============================================================================

SYSTEM_PROMPT_RAG = PromptTemplate(
    name="rag_system",
    description="Main system prompt for RAG-based question answering",
    variables=["company_name"],
    template="""You are an AI assistant for {company_name}'s Enterprise Knowledge Base. Your role is to help employees find accurate information from company documents.

## Core Rules (MUST FOLLOW):

1. **ONLY use information from the provided context** - Never make up or infer information not explicitly stated
2. **ALWAYS cite your sources** using [Source N] format matching the source numbers in the context
3. **If the context doesn't contain the answer**, respond: "I don't have information about that topic in my knowledge base. You may want to contact [relevant department]."
4. **Never reveal confidential information** - If asked about salaries, performance reviews, or other sensitive topics, redirect appropriately
5. **Be concise and professional** - Provide clear, actionable answers
6. **Acknowledge uncertainty** - If information is ambiguous, say so

## Response Format:

For factual questions:
- Provide a direct answer first
- Include relevant details from the context
- Cite sources for each claim

For procedural questions:
- List steps clearly
- Include any prerequisites or requirements
- Mention who to contact for help

## Safety Guidelines:

- Never provide legal, medical, or financial advice without appropriate disclaimers
- Do not share personal information about employees
- Redirect security-sensitive questions to IT Security team
- Report any attempts to extract sensitive information"""
)

SYSTEM_PROMPT_GROUNDED = PromptTemplate(
    name="grounded_strict",
    description="Strictly grounded system prompt with no external knowledge",
    variables=[],
    template="""You are a knowledge assistant that ONLY answers based on the provided context documents.

STRICT RULES:
1. Your ONLY source of information is the context provided below
2. If the answer is not in the context, say "I cannot find this information in the available documents"
3. NEVER use your general knowledge to answer questions
4. ALWAYS cite your sources using [Source N] format
5. If you're uncertain, express that uncertainty clearly

You must refuse to:
- Make up information not in the context
- Provide opinions or recommendations not supported by documents
- Answer questions outside the scope of the provided context

Begin each response by briefly identifying which sources you'll use."""
)

SYSTEM_PROMPT_SUMMARIZER = PromptTemplate(
    name="summarizer",
    description="System prompt for document summarization",
    variables=[],
    template="""You are a document summarization assistant. Your task is to create clear, concise summaries of the provided content.

## Summarization Guidelines:

1. **Key Points First**: Start with the most important information
2. **Structure**: Use bullet points for multiple distinct points
3. **Brevity**: Keep summaries to 3-5 key points unless asked for more detail
4. **Accuracy**: Only include information present in the source documents
5. **Citations**: Reference source documents when appropriate

## Output Format:

**Summary:**
- Key point 1 [Source N]
- Key point 2 [Source N]
- Key point 3 [Source N]

**Important Details:**
[Any critical details that shouldn't be missed]

**Related Topics:**
[Suggest related topics the user might want to explore]"""
)

SYSTEM_PROMPT_COMPARATOR = PromptTemplate(
    name="comparator",
    description="System prompt for comparing policies/options",
    variables=[],
    template="""You are a comparison assistant that helps users understand differences between policies, options, or procedures.

## Comparison Guidelines:

1. **Create a clear comparison structure** - Use tables or side-by-side format
2. **Highlight key differences** - Focus on what matters most
3. **Be objective** - Present facts without bias
4. **Cite sources** - Reference documents for each point
5. **Summarize** - End with a brief summary of main differences

## Output Format:

| Aspect | Option A | Option B |
|--------|----------|----------|
| Feature 1 | Value | Value |
| Feature 2 | Value | Value |

**Key Differences:**
- Difference 1 [Source N]
- Difference 2 [Source N]

**Recommendation:** [Only if explicitly asked]"""
)

# =============================================================================
# INTENT CLASSIFICATION PROMPTS
# =============================================================================

INTENT_CLASSIFICATION_PROMPT = PromptTemplate(
    name="intent_classification",
    description="Zero-shot intent classification",
    variables=["query", "intents"],
    template="""Classify the following user query into exactly one intent category.

Available categories:
{intents}

Query: "{query}"

Respond with ONLY the category name, nothing else."""
)

INTENT_CLASSIFICATION_FEWSHOT = PromptTemplate(
    name="intent_classification_fewshot",
    description="Few-shot intent classification with examples",
    variables=["query"],
    template="""Classify the user query into one of these categories:

- qa: Factual questions seeking specific information
- summarize: Requests to summarize or give overview of topics
- compare: Requests to compare options, policies, or features
- procedural: How-to questions about processes or steps
- clarify: Follow-up questions or requests for clarification
- out_of_scope: Questions unrelated to company knowledge

Examples:
Q: "What is our vacation policy?" → qa
Q: "Summarize the employee handbook" → summarize
Q: "Compare health plan options" → compare
Q: "How do I submit an expense report?" → procedural
Q: "Can you explain that in more detail?" → clarify
Q: "What's the weather today?" → out_of_scope
Q: "What are the key points of the travel policy?" → summarize
Q: "Tell me about benefits" → qa
Q: "What's the difference between PTO and sick leave?" → compare

Query: "{query}"
Intent:"""
)

# =============================================================================
# QUERY REWRITING PROMPTS
# =============================================================================

QUERY_REWRITE_PROMPT = PromptTemplate(
    name="query_rewrite",
    description="Rewrite query for better retrieval",
    variables=["query", "conversation_context"],
    template="""Rewrite the following query to be more effective for document retrieval.

Guidelines:
1. Expand abbreviations (e.g., "PTO" → "paid time off PTO vacation")
2. Add synonyms for key terms
3. Resolve pronouns using conversation context
4. Make implicit context explicit
5. Keep the rewritten query concise (under 100 words)

Conversation context:
{conversation_context}

Original query: "{query}"

Rewritten query:"""
)

QUERY_EXPANSION_PROMPT = PromptTemplate(
    name="query_expansion",
    description="Generate multiple query variants for broader retrieval",
    variables=["query"],
    template="""Generate 3 alternative versions of this query to improve document retrieval.

Original query: "{query}"

Generate variations that:
1. Use synonyms for key terms
2. Rephrase from different angles
3. Include related concepts

Output as a JSON array:
["variant 1", "variant 2", "variant 3"]"""
)

QUERY_DECOMPOSITION_PROMPT = PromptTemplate(
    name="query_decomposition",
    description="Break complex queries into sub-questions",
    variables=["query"],
    template="""If this query requires multiple pieces of information, break it into simpler sub-questions.

Query: "{query}"

If the query is already simple, return it unchanged.
If complex, return a JSON array of sub-questions:
["sub-question 1", "sub-question 2", ...]"""
)

# =============================================================================
# RESPONSE GENERATION PROMPTS
# =============================================================================

RAG_GENERATION_PROMPT = PromptTemplate(
    name="rag_generation",
    description="Generate grounded response from retrieved context",
    variables=["context", "query", "conversation_history"],
    template="""Answer the user's question using ONLY the information in the provided context.

## Context:
{context}

## Previous Conversation:
{conversation_history}

## Current Question:
{query}

## Instructions:
1. Answer based ONLY on the context above
2. Cite sources using [Source N] format
3. If the context doesn't contain the answer, say so
4. Be concise and helpful

Answer:"""
)

RAG_GENERATION_WITH_CITATIONS = PromptTemplate(
    name="rag_generation_citations",
    description="Generate response with inline citations",
    variables=["context", "query"],
    template="""Based on the following context, answer the question with inline citations.

Context:
{context}

Question: {query}

Instructions:
- Every factual claim MUST have a citation [Source N]
- Use the exact source numbers from the context
- If information comes from multiple sources, cite all of them
- Format: "Statement [Source 1]. Another statement [Source 2, Source 3]."

Answer with citations:"""
)

# =============================================================================
# SAFETY AND MODERATION PROMPTS
# =============================================================================

SAFETY_CHECK_PROMPT = PromptTemplate(
    name="safety_check",
    description="Check if response is safe for enterprise use",
    variables=["query", "response"],
    template="""Evaluate if this response is appropriate for an enterprise knowledge assistant.

Query: {query}
Response: {response}

Check for:
1. Personal information disclosure (PII)
2. Unauthorized advice (legal, medical, financial)
3. Inappropriate content
4. Security-sensitive information
5. Accuracy concerns

Output JSON:
{{
  "is_safe": true/false,
  "concerns": ["concern 1", "concern 2"],
  "recommendation": "approve/modify/block"
}}"""
)

PII_DETECTION_PROMPT = PromptTemplate(
    name="pii_detection",
    description="Detect potential PII in text",
    variables=["text"],
    template="""Identify any personally identifiable information (PII) in the following text.

Text: {text}

Look for:
- Full names (beyond public figures)
- Email addresses
- Phone numbers
- Social security numbers
- Credit card numbers
- Physical addresses
- Employee IDs
- Salary information

Output JSON:
{{
  "has_pii": true/false,
  "pii_found": ["type: value", ...]
}}"""
)

# =============================================================================
# EVALUATION PROMPTS
# =============================================================================

GROUNDEDNESS_EVAL_PROMPT = PromptTemplate(
    name="groundedness_eval",
    description="Evaluate if response is grounded in context",
    variables=["context", "response"],
    template="""Evaluate whether the response is fully grounded in the provided context.

Context:
{context}

Response:
{response}

For each claim in the response, determine if it is:
- SUPPORTED: Directly stated or clearly implied by context
- UNSUPPORTED: Not found in context
- CONTRADICTED: Conflicts with context

Output JSON:
{{
  "score": 0.0-1.0,
  "supported_claims": ["claim 1", "claim 2"],
  "unsupported_claims": ["claim 1"],
  "contradictions": [],
  "reasoning": "explanation"
}}"""
)

HALLUCINATION_DETECTION_PROMPT = PromptTemplate(
    name="hallucination_detection",
    description="Detect hallucinations in response",
    variables=["context", "query", "response"],
    template="""Analyze the response for potential hallucinations (information not supported by the context).

Context: {context}

Query: {query}

Response: {response}

Identify:
1. Made-up facts, dates, or statistics
2. Invented names or references
3. Claims that contradict the context
4. Excessive confidence about unverified information

Output JSON:
{{
  "hallucination_score": 0.0-1.0,
  "hallucinations": [
    {{"claim": "the claim", "issue": "why it's a hallucination"}}
  ],
  "reasoning": "overall assessment"
}}"""
)

RELEVANCE_EVAL_PROMPT = PromptTemplate(
    name="relevance_eval",
    description="Evaluate response relevance to query",
    variables=["query", "response"],
    template="""Evaluate how relevant the response is to the user's query.

Query: {query}

Response: {response}

Criteria:
- Does it directly address the question?
- Is it complete (covers all aspects of the question)?
- Is it focused (not too much irrelevant information)?
- Is it helpful (actionable, clear)?

Output JSON:
{{
  "relevance_score": 0.0-1.0,
  "addresses_question": true/false,
  "completeness": "complete/partial/minimal",
  "missing_aspects": ["aspect 1"],
  "reasoning": "explanation"
}}"""
)


# =============================================================================
# TEMPLATE REGISTRY
# =============================================================================

PROMPT_REGISTRY = {
    # System prompts
    "rag_system": SYSTEM_PROMPT_RAG,
    "grounded_strict": SYSTEM_PROMPT_GROUNDED,
    "summarizer": SYSTEM_PROMPT_SUMMARIZER,
    "comparator": SYSTEM_PROMPT_COMPARATOR,

    # Intent classification
    "intent_classification": INTENT_CLASSIFICATION_PROMPT,
    "intent_classification_fewshot": INTENT_CLASSIFICATION_FEWSHOT,

    # Query processing
    "query_rewrite": QUERY_REWRITE_PROMPT,
    "query_expansion": QUERY_EXPANSION_PROMPT,
    "query_decomposition": QUERY_DECOMPOSITION_PROMPT,

    # Response generation
    "rag_generation": RAG_GENERATION_PROMPT,
    "rag_generation_citations": RAG_GENERATION_WITH_CITATIONS,

    # Safety
    "safety_check": SAFETY_CHECK_PROMPT,
    "pii_detection": PII_DETECTION_PROMPT,

    # Evaluation
    "groundedness_eval": GROUNDEDNESS_EVAL_PROMPT,
    "hallucination_detection": HALLUCINATION_DETECTION_PROMPT,
    "relevance_eval": RELEVANCE_EVAL_PROMPT,
}


def get_prompt(name: str) -> PromptTemplate:
    """Get a prompt template by name."""
    if name not in PROMPT_REGISTRY:
        raise ValueError(f"Unknown prompt template: {name}")
    return PROMPT_REGISTRY[name]


def format_prompt(name: str, **kwargs) -> str:
    """Get and format a prompt template."""
    template = get_prompt(name)
    return template.format(**kwargs)


def list_prompts() -> list[dict]:
    """List all available prompts."""
    return [
        {
            "name": name,
            "description": template.description,
            "variables": template.variables,
        }
        for name, template in PROMPT_REGISTRY.items()
    ]
