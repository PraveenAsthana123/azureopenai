"""
Cosmos DB Conversation History Tool.

Manages conversation history for:
- Query rewriting (follow-up resolution)
- Context assembly
- Audit logging
"""

import os
import logging
from typing import TypedDict

from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential

logger = logging.getLogger(__name__)


class ConversationTurn(TypedDict):
    id: str
    session_id: str
    user_id: str
    tenant_id: str
    user_message: str
    assistant_message: str
    timestamp: str
    metadata: dict


# Configuration
COSMOS_URI = os.getenv("COSMOS_URI")
COSMOS_DB = os.getenv("COSMOS_DB", "rag_platform")
COSMOS_CONTAINER = os.getenv("COSMOS_CONTAINER", "conversations")

# Lazy-initialized clients
_cosmos_client = None
_container = None


async def get_container():
    """Get or create Cosmos DB container client."""
    global _cosmos_client, _container

    if _container:
        return _container

    credential = DefaultAzureCredential()
    _cosmos_client = CosmosClient(COSMOS_URI, credential=credential)
    database = _cosmos_client.get_database_client(COSMOS_DB)
    _container = database.get_container_client(COSMOS_CONTAINER)

    return _container


async def get_last_messages(
    session_id: str,
    limit: int = 5
) -> list[ConversationTurn]:
    """
    Retrieve last N messages for a session.

    Args:
        session_id: Session identifier
        limit: Maximum number of messages to retrieve

    Returns:
        List of conversation turns (oldest to newest)
    """
    if not session_id:
        return []

    try:
        container = await get_container()

        query = """
            SELECT TOP @limit *
            FROM c
            WHERE c.session_id = @session_id
            ORDER BY c._ts DESC
        """

        parameters = [
            {"name": "@session_id", "value": session_id},
            {"name": "@limit", "value": limit}
        ]

        items = container.query_items(
            query=query,
            parameters=parameters,
            partition_key=session_id
        )

        messages = []
        async for item in items:
            messages.append({
                "id": item.get("id"),
                "session_id": item.get("session_id"),
                "user_id": item.get("user_id"),
                "tenant_id": item.get("tenant_id"),
                "user_message": item.get("user_message", ""),
                "assistant_message": item.get("assistant_message", ""),
                "timestamp": item.get("timestamp", ""),
                "metadata": item.get("metadata", {})
            })

        # Return in chronological order (oldest first)
        return list(reversed(messages))

    except Exception as e:
        logger.warning(f"Failed to retrieve conversation history: {e}")
        return []


async def save_turn(
    session_id: str,
    user_id: str,
    tenant_id: str,
    user_message: str,
    assistant_message: str,
    metadata: dict = None
) -> str:
    """
    Save a conversation turn to Cosmos DB.

    Args:
        session_id: Session identifier
        user_id: User identifier
        tenant_id: Tenant identifier
        user_message: User's message
        assistant_message: Assistant's response
        metadata: Additional metadata

    Returns:
        Document ID of saved turn
    """
    import uuid
    from datetime import datetime

    try:
        container = await get_container()

        doc_id = str(uuid.uuid4())
        document = {
            "id": doc_id,
            "session_id": session_id,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "user_message": user_message,
            "assistant_message": assistant_message,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }

        await container.create_item(body=document)
        return doc_id

    except Exception as e:
        logger.error(f"Failed to save conversation turn: {e}")
        raise


async def get_session_summary(session_id: str) -> dict:
    """
    Get summary statistics for a session.

    Args:
        session_id: Session identifier

    Returns:
        Summary with turn count, duration, etc.
    """
    try:
        container = await get_container()

        query = """
            SELECT
                COUNT(1) as turn_count,
                MIN(c._ts) as first_ts,
                MAX(c._ts) as last_ts
            FROM c
            WHERE c.session_id = @session_id
        """

        parameters = [{"name": "@session_id", "value": session_id}]

        items = container.query_items(
            query=query,
            parameters=parameters,
            partition_key=session_id
        )

        async for item in items:
            return {
                "session_id": session_id,
                "turn_count": item.get("turn_count", 0),
                "first_timestamp": item.get("first_ts"),
                "last_timestamp": item.get("last_ts")
            }

        return {"session_id": session_id, "turn_count": 0}

    except Exception as e:
        logger.warning(f"Failed to get session summary: {e}")
        return {"session_id": session_id, "turn_count": 0}


if __name__ == "__main__":
    import asyncio

    async def test():
        # Test retrieval
        messages = await get_last_messages("test-session", limit=3)
        print(f"Retrieved {len(messages)} messages")
        for msg in messages:
            print(f"  User: {msg['user_message'][:50]}...")
            print(f"  Assistant: {msg['assistant_message'][:50]}...")

    asyncio.run(test())
