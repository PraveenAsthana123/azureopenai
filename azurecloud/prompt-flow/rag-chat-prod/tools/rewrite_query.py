"""
Query Rewrite Tool for Prompt Flow.

Resolves coreferences in follow-up queries using conversation history.
Transforms ambiguous queries into standalone searchable queries.
"""

from typing import TypedDict

from tools.cosmos_history import get_last_messages


class RewriteOutput(TypedDict):
    transformed_query: str
    was_rewritten: bool
    original_query: str


async def rewrite_query(
    question: str,
    intent: str,
    session_id: str,
    user_id: str
) -> RewriteOutput:
    """
    Rewrite follow-up queries to be standalone.

    Args:
        question: Original user question
        intent: Classified intent (from classify_intent)
        session_id: Session ID for history lookup
        user_id: User ID

    Returns:
        RewriteOutput with transformed query
    """
    # Only rewrite follow-up queries
    if intent != "follow_up":
        return {
            "transformed_query": question,
            "was_rewritten": False,
            "original_query": question
        }

    # Get conversation history
    history = await get_last_messages(session_id, limit=3)

    if not history:
        # No history available - return original
        return {
            "transformed_query": question,
            "was_rewritten": False,
            "original_query": question
        }

    # Extract recent context
    recent_topics = []
    for turn in history[-2:]:
        user_msg = turn.get("user_message", "")
        assistant_msg = turn.get("assistant_message", "")

        # Extract key nouns/topics from previous messages
        if user_msg:
            recent_topics.append(user_msg)

    if not recent_topics:
        return {
            "transformed_query": question,
            "was_rewritten": False,
            "original_query": question
        }

    # Simple coreference resolution
    transformed = _resolve_coreferences(question, recent_topics)

    return {
        "transformed_query": transformed,
        "was_rewritten": transformed != question,
        "original_query": question
    }


def _resolve_coreferences(question: str, context: list[str]) -> str:
    """
    Simple coreference resolution.

    Replaces pronouns and references with actual subjects from context.
    """
    q_lower = question.lower()

    # Common coreference patterns
    coreference_words = [
        "that", "this", "it", "they", "those", "these",
        "the same", "similar", "related"
    ]

    needs_context = any(word in q_lower for word in coreference_words)

    if not needs_context:
        return question

    # Get the most recent topic
    if context:
        last_context = context[-1]

        # Extract the main subject from context (simplified)
        # In production, use NLP or LLM for better extraction
        main_subject = _extract_subject(last_context)

        if main_subject:
            # Replace coreferences with subject
            transformed = question

            # Replace pronouns
            replacements = [
                ("what about it", f"what about {main_subject}"),
                ("what about that", f"what about {main_subject}"),
                ("tell me more", f"tell me more about {main_subject}"),
                ("more on that", f"more on {main_subject}"),
                ("the same", main_subject),
                ("that", main_subject),
                ("it", main_subject),
            ]

            for old, new in replacements:
                if old in transformed.lower():
                    # Preserve case
                    transformed = transformed.replace(old, new)
                    transformed = transformed.replace(old.capitalize(), new.capitalize())
                    break

            return transformed

    # Fallback: append context
    context_str = " ".join(context[-1:])
    return f"{question} (Context: {context_str})"


def _extract_subject(text: str) -> str | None:
    """
    Extract main subject from a sentence.

    Simplified implementation - in production, use spaCy or similar.
    """
    # Common question patterns to extract subject
    import re

    patterns = [
        r"what is (?:the )?(.+?)(?:\?|$)",
        r"(?:tell me about|explain|describe) (?:the )?(.+?)(?:\?|$)",
        r"how (?:do|does|to) (.+?)(?:\?|$)",
        r"(?:^|\s)the (.+?) (?:policy|procedure|process|document)",
    ]

    text_lower = text.lower().strip()

    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            subject = match.group(1).strip()
            # Clean up
            subject = re.sub(r'^(a|an|the)\s+', '', subject)
            if len(subject) > 3 and len(subject) < 50:
                return subject

    # Fallback: return first few meaningful words
    words = text_lower.split()
    # Skip common words
    skip_words = {"what", "how", "when", "where", "why", "is", "are", "the", "a", "an", "do", "does"}
    meaningful = [w for w in words[:10] if w not in skip_words and len(w) > 2]

    if meaningful:
        return " ".join(meaningful[:3])

    return None


# Prompt Flow entry point
async def main(
    question: str,
    intent: str,
    session_id: str,
    user_id: str
) -> RewriteOutput:
    """Entry point for Prompt Flow."""
    return await rewrite_query(question, intent, session_id, user_id)


if __name__ == "__main__":
    import asyncio

    async def test():
        # Test cases
        test_cases = [
            {
                "question": "What about that?",
                "intent": "follow_up",
                "session_id": "test",
                "user_id": "test"
            },
            {
                "question": "What is the retention policy?",
                "intent": "doc_search",
                "session_id": "test",
                "user_id": "test"
            }
        ]

        for case in test_cases:
            result = await rewrite_query(**case)
            print(f"Original: '{case['question']}'")
            print(f"Transformed: '{result['transformed_query']}'")
            print(f"Rewritten: {result['was_rewritten']}")
            print()

    asyncio.run(test())
