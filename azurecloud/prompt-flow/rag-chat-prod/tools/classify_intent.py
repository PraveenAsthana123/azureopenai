"""
Intent Classification Tool for Prompt Flow.

Classifies user queries into categories:
- greeting: Social greetings
- doc_search: Document/knowledge retrieval queries
- follow_up: Follow-up questions referencing previous context
- general: General questions
"""

import re
from typing import TypedDict


class IntentOutput(TypedDict):
    intent: str
    confidence: float


def classify_intent(question: str) -> IntentOutput:
    """
    Classify the intent of a user question.

    Args:
        question: User's natural language question

    Returns:
        IntentOutput with intent type and confidence score
    """
    q = question.strip().lower()

    # Greeting patterns
    greeting_patterns = [
        r"^(hi|hello|hey|good (morning|afternoon|evening)|howdy|greetings)\b",
        r"^(what'?s up|how are you|how'?s it going)\b",
    ]

    # Follow-up patterns (references to previous context)
    followup_patterns = [
        r"^(that|those|it|they|this|these)\b",
        r"^(what about|how about|more on|tell me more)\b",
        r"^(can you explain|elaborate on|expand on)\b",
        r"(mentioned|said|talked about) (earlier|before|above)\b",
        r"^(and|also|additionally)\b",
        r"(the same|similar|related)\b",
    ]

    # Document search patterns
    doc_search_patterns = [
        r"\b(find|search|locate|look up|retrieve)\b",
        r"\b(document|file|pdf|report|policy|procedure)\b",
        r"\b(what (is|are|does)|how (do|does|to)|where (is|are))\b",
        r"\b(when|why|which|who)\b",
        r"\b(according to|based on|per the)\b",
    ]

    # Check greeting
    for pattern in greeting_patterns:
        if re.search(pattern, q):
            return {"intent": "greeting", "confidence": 0.95}

    # Check follow-up
    for pattern in followup_patterns:
        if re.search(pattern, q):
            return {"intent": "follow_up", "confidence": 0.85}

    # Check document search
    for pattern in doc_search_patterns:
        if re.search(pattern, q):
            return {"intent": "doc_search", "confidence": 0.80}

    # Default to general
    return {"intent": "general", "confidence": 0.70}


# Prompt Flow entry point
def main(question: str) -> IntentOutput:
    """Entry point for Prompt Flow."""
    return classify_intent(question)


if __name__ == "__main__":
    # Test cases
    test_queries = [
        "Hello!",
        "What is the retention policy?",
        "Tell me more about that",
        "Find the security document",
        "What about the budget?",
    ]

    for query in test_queries:
        result = classify_intent(query)
        print(f"'{query}' -> {result}")
