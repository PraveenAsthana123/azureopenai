"""
Context Assembly Tool for Prompt Flow.

Builds grounded prompts with:
- Conversation history
- Retrieved chunks
- Citation-aware formatting
"""

import os
from typing import TypedDict

from tools.cosmos_history import get_last_messages


class ContextOutput(TypedDict):
    prompt: str
    system_prompt: str
    context_text: str
    history_turns: int
    chunk_count: int


# System prompt template
SYSTEM_PROMPT = """You are an intelligent enterprise assistant that answers questions using only the provided source documents.

## CRITICAL RULES:
1. **Only use information from the provided sources.** Do not use any external knowledge.
2. **Cite every factual claim** using the format: [Source: filename.pdf, Page X]
3. **If information is not in the sources**, say: "I don't have enough information in the available documents to answer this question."
4. **Never fabricate** sources, page numbers, or facts.
5. **Preserve table structure** when answering questions about tabular data.
6. **For images/figures**, reference as: [See Figure N on Page X]

## RESPONSE FORMAT:
- Be concise but complete
- Use bullet points for lists
- Include relevant quotes from sources when helpful
- Always end with source citations
"""


def format_chunks(chunks: list[dict]) -> str:
    """Format retrieved chunks for the prompt."""
    if not chunks:
        return "No relevant sources found."

    formatted = []
    for i, chunk in enumerate(chunks, 1):
        metadata = chunk.get("metadata", {})
        source = metadata.get("source_pdf", "unknown.pdf")
        page = metadata.get("page_number", "?")
        content_type = chunk.get("content_type", "text")

        header = f"[Source {i}: {source}, Page {page}]"
        if content_type == "table":
            header += " (Table)"
        elif content_type == "image":
            header += " (Figure)"

        formatted.append(f"{header}\n{chunk.get('content', '')}")

    return "\n\n---\n\n".join(formatted)


def format_history(history: list[dict]) -> str:
    """Format conversation history."""
    if not history:
        return ""

    turns = []
    for msg in history[-5:]:  # Last 5 turns
        user_msg = msg.get("user_message", "")
        assistant_msg = msg.get("assistant_message", "")
        if user_msg:
            turns.append(f"User: {user_msg}")
        if assistant_msg:
            # Truncate long responses
            truncated = assistant_msg[:500] + "..." if len(assistant_msg) > 500 else assistant_msg
            turns.append(f"Assistant: {truncated}")

    return "\n".join(turns)


async def build_context(
    question: str,
    transformed_query: str,
    chunks: list[dict],
    session_id: str,
    user_id: str
) -> ContextOutput:
    """
    Build grounded prompt with history and retrieved context.

    Args:
        question: Original user question
        transformed_query: Rewritten query (may differ for follow-ups)
        chunks: Retrieved document chunks
        session_id: Session ID for history lookup
        user_id: User ID

    Returns:
        ContextOutput with prompt and metadata
    """
    # Get conversation history
    history = await get_last_messages(session_id, limit=5)
    history_text = format_history(history)

    # Format retrieved sources
    sources_text = format_chunks(chunks)

    # Build the user prompt
    user_prompt_parts = []

    if history_text:
        user_prompt_parts.append(f"## Previous Conversation:\n{history_text}")

    user_prompt_parts.append(f"## Retrieved Sources:\n{sources_text}")

    # Include transformed query if different (helps with follow-ups)
    if transformed_query != question:
        user_prompt_parts.append(f"## Context Note:\nThe query was interpreted as: \"{transformed_query}\"")

    user_prompt_parts.append(f"## Current Question:\n{question}")
    user_prompt_parts.append("## Your Response:")

    user_prompt = "\n\n".join(user_prompt_parts)

    return {
        "prompt": user_prompt,
        "system_prompt": SYSTEM_PROMPT,
        "context_text": sources_text,  # For evaluation
        "history_turns": len(history),
        "chunk_count": len(chunks)
    }


# Prompt Flow entry point
async def main(
    question: str,
    transformed_query: str,
    chunks: list[dict],
    session_id: str,
    user_id: str
) -> ContextOutput:
    """Entry point for Prompt Flow."""
    return await build_context(question, transformed_query, chunks, session_id, user_id)


if __name__ == "__main__":
    import asyncio

    async def test():
        result = await build_context(
            question="What is the retention policy?",
            transformed_query="What is the retention policy?",
            chunks=[
                {
                    "content": "Logs are retained for 365 days per compliance requirements.",
                    "metadata": {"source_pdf": "policy.pdf", "page_number": 4},
                    "content_type": "text"
                }
            ],
            session_id="test-session",
            user_id="test@company.com"
        )
        print("System Prompt:")
        print(result["system_prompt"][:200] + "...")
        print("\nUser Prompt:")
        print(result["prompt"])

    asyncio.run(test())
