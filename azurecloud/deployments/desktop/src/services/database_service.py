"""
Database Service - Unified interface for conversation storage.

Supports:
- SQLite (local, offline)
- Azure Cosmos DB (cloud)
- PostgreSQL (hybrid)

Stores conversation history, sessions, and user data.
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Chat message model."""
    id: str
    session_id: str
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime
    metadata: dict = field(default_factory=dict)


@dataclass
class Session:
    """Conversation session model."""
    id: str
    user_id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    metadata: dict = field(default_factory=dict)


class BaseDatabaseService(ABC):
    """Abstract base class for database services."""

    @abstractmethod
    async def create_session(
        self, user_id: str, title: Optional[str] = None
    ) -> Session:
        """Create a new conversation session."""
        pass

    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        pass

    @abstractmethod
    async def list_sessions(
        self, user_id: str, limit: int = 50
    ) -> list[Session]:
        """List sessions for a user."""
        pass

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and its messages."""
        pass

    @abstractmethod
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> Message:
        """Add a message to a session."""
        pass

    @abstractmethod
    async def get_messages(
        self,
        session_id: str,
        limit: int = 100
    ) -> list[Message]:
        """Get messages for a session."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if database is available."""
        pass


class SQLiteService(BaseDatabaseService):
    """
    SQLite local database service.

    Lightweight, file-based storage for development and small deployments.
    """

    def __init__(self, database_path: str = "./data/rag.db"):
        self.database_path = database_path
        self._engine = None
        self._initialized = False

    async def _get_engine(self):
        """Get or create SQLAlchemy async engine."""
        if self._engine is None:
            from sqlalchemy.ext.asyncio import create_async_engine
            import os

            # Ensure directory exists
            os.makedirs(os.path.dirname(self.database_path), exist_ok=True)

            self._engine = create_async_engine(
                f"sqlite+aiosqlite:///{self.database_path}",
                echo=False
            )

        if not self._initialized:
            await self._init_tables()
            self._initialized = True

        return self._engine

    async def _init_tables(self):
        """Initialize database tables."""
        from sqlalchemy import text

        engine = self._engine
        async with engine.begin() as conn:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}'
                )
            """))

            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """))

            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user
                ON sessions(user_id)
            """))

            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id)
            """))

        logger.info("SQLite tables initialized")

    async def create_session(
        self, user_id: str, title: Optional[str] = None
    ) -> Session:
        """Create a new conversation session."""
        from sqlalchemy import text

        engine = await self._get_engine()
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()

        async with engine.begin() as conn:
            await conn.execute(
                text("""
                    INSERT INTO sessions (id, user_id, title, created_at, updated_at)
                    VALUES (:id, :user_id, :title, :created_at, :updated_at)
                """),
                {
                    "id": session_id,
                    "user_id": user_id,
                    "title": title,
                    "created_at": now,
                    "updated_at": now
                }
            )

        return Session(
            id=session_id,
            user_id=user_id,
            title=title,
            created_at=now,
            updated_at=now
        )

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        from sqlalchemy import text

        engine = await self._get_engine()

        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT * FROM sessions WHERE id = :id"),
                {"id": session_id}
            )
            row = result.fetchone()

            if not row:
                return None

            return Session(
                id=row[0],
                user_id=row[1],
                title=row[2],
                created_at=row[3],
                updated_at=row[4],
                metadata=json.loads(row[5]) if row[5] else {}
            )

    async def list_sessions(
        self, user_id: str, limit: int = 50
    ) -> list[Session]:
        """List sessions for a user."""
        from sqlalchemy import text

        engine = await self._get_engine()

        async with engine.connect() as conn:
            result = await conn.execute(
                text("""
                    SELECT * FROM sessions
                    WHERE user_id = :user_id
                    ORDER BY updated_at DESC
                    LIMIT :limit
                """),
                {"user_id": user_id, "limit": limit}
            )

            return [
                Session(
                    id=row[0],
                    user_id=row[1],
                    title=row[2],
                    created_at=row[3],
                    updated_at=row[4],
                    metadata=json.loads(row[5]) if row[5] else {}
                )
                for row in result.fetchall()
            ]

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and its messages."""
        from sqlalchemy import text

        engine = await self._get_engine()

        async with engine.begin() as conn:
            # Delete messages first
            await conn.execute(
                text("DELETE FROM messages WHERE session_id = :id"),
                {"id": session_id}
            )
            # Delete session
            result = await conn.execute(
                text("DELETE FROM sessions WHERE id = :id"),
                {"id": session_id}
            )
            return result.rowcount > 0

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> Message:
        """Add a message to a session."""
        from sqlalchemy import text

        engine = await self._get_engine()
        message_id = str(uuid.uuid4())
        now = datetime.utcnow()

        async with engine.begin() as conn:
            await conn.execute(
                text("""
                    INSERT INTO messages (id, session_id, role, content, timestamp, metadata)
                    VALUES (:id, :session_id, :role, :content, :timestamp, :metadata)
                """),
                {
                    "id": message_id,
                    "session_id": session_id,
                    "role": role,
                    "content": content,
                    "timestamp": now,
                    "metadata": json.dumps(metadata or {})
                }
            )

            # Update session timestamp
            await conn.execute(
                text("UPDATE sessions SET updated_at = :now WHERE id = :id"),
                {"now": now, "id": session_id}
            )

        return Message(
            id=message_id,
            session_id=session_id,
            role=role,
            content=content,
            timestamp=now,
            metadata=metadata or {}
        )

    async def get_messages(
        self,
        session_id: str,
        limit: int = 100
    ) -> list[Message]:
        """Get messages for a session."""
        from sqlalchemy import text

        engine = await self._get_engine()

        async with engine.connect() as conn:
            result = await conn.execute(
                text("""
                    SELECT * FROM messages
                    WHERE session_id = :session_id
                    ORDER BY timestamp ASC
                    LIMIT :limit
                """),
                {"session_id": session_id, "limit": limit}
            )

            return [
                Message(
                    id=row[0],
                    session_id=row[1],
                    role=row[2],
                    content=row[3],
                    timestamp=row[4],
                    metadata=json.loads(row[5]) if row[5] else {}
                )
                for row in result.fetchall()
            ]

    async def health_check(self) -> bool:
        """Check if SQLite database is accessible."""
        try:
            await self._get_engine()
            return True
        except Exception as e:
            logger.warning(f"SQLite health check failed: {e}")
            return False


class CosmosDBService(BaseDatabaseService):
    """
    Azure Cosmos DB service.

    Enterprise-grade, globally distributed database.
    """

    def __init__(
        self,
        endpoint: str,
        key: Optional[str] = None,
        database_name: str = "rag_platform",
        container_name: str = "conversations",
        use_managed_identity: bool = False
    ):
        self.endpoint = endpoint
        self.key = key
        self.database_name = database_name
        self.container_name = container_name
        self.use_managed_identity = use_managed_identity
        self._client = None
        self._container = None

    async def _get_container(self):
        """Get Cosmos DB container."""
        if self._container is not None:
            return self._container

        from azure.cosmos.aio import CosmosClient

        if self.key:
            self._client = CosmosClient(self.endpoint, credential=self.key)
        else:
            from azure.identity.aio import DefaultAzureCredential
            credential = DefaultAzureCredential()
            self._client = CosmosClient(self.endpoint, credential=credential)

        database = self._client.get_database_client(self.database_name)
        self._container = database.get_container_client(self.container_name)

        return self._container

    async def create_session(
        self, user_id: str, title: Optional[str] = None
    ) -> Session:
        """Create a new conversation session."""
        container = await self._get_container()

        session_id = str(uuid.uuid4())
        now = datetime.utcnow()

        item = {
            "id": session_id,
            "type": "session",
            "user_id": user_id,
            "title": title,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "metadata": {}
        }

        await container.create_item(body=item, partition_key=user_id)

        return Session(
            id=session_id,
            user_id=user_id,
            title=title,
            created_at=now,
            updated_at=now
        )

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        container = await self._get_container()

        try:
            # Query to find session by ID
            query = "SELECT * FROM c WHERE c.id = @id AND c.type = 'session'"
            items = container.query_items(
                query=query,
                parameters=[{"name": "@id", "value": session_id}]
            )

            async for item in items:
                return Session(
                    id=item["id"],
                    user_id=item["user_id"],
                    title=item.get("title"),
                    created_at=datetime.fromisoformat(item["created_at"]),
                    updated_at=datetime.fromisoformat(item["updated_at"]),
                    metadata=item.get("metadata", {})
                )

            return None
        except Exception:
            return None

    async def list_sessions(
        self, user_id: str, limit: int = 50
    ) -> list[Session]:
        """List sessions for a user."""
        container = await self._get_container()

        query = """
            SELECT * FROM c
            WHERE c.user_id = @user_id AND c.type = 'session'
            ORDER BY c.updated_at DESC
            OFFSET 0 LIMIT @limit
        """

        items = container.query_items(
            query=query,
            parameters=[
                {"name": "@user_id", "value": user_id},
                {"name": "@limit", "value": limit}
            ],
            partition_key=user_id
        )

        sessions = []
        async for item in items:
            sessions.append(Session(
                id=item["id"],
                user_id=item["user_id"],
                title=item.get("title"),
                created_at=datetime.fromisoformat(item["created_at"]),
                updated_at=datetime.fromisoformat(item["updated_at"]),
                metadata=item.get("metadata", {})
            ))

        return sessions

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and its messages."""
        container = await self._get_container()

        try:
            # Get session to find user_id (partition key)
            session = await self.get_session(session_id)
            if not session:
                return False

            # Delete all messages for session
            query = "SELECT * FROM c WHERE c.session_id = @session_id AND c.type = 'message'"
            items = container.query_items(
                query=query,
                parameters=[{"name": "@session_id", "value": session_id}]
            )

            async for item in items:
                await container.delete_item(
                    item=item["id"],
                    partition_key=session.user_id
                )

            # Delete session
            await container.delete_item(
                item=session_id,
                partition_key=session.user_id
            )

            return True
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> Message:
        """Add a message to a session."""
        container = await self._get_container()

        # Get session to find user_id
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        message_id = str(uuid.uuid4())
        now = datetime.utcnow()

        item = {
            "id": message_id,
            "type": "message",
            "session_id": session_id,
            "user_id": session.user_id,
            "role": role,
            "content": content,
            "timestamp": now.isoformat(),
            "metadata": metadata or {}
        }

        await container.create_item(body=item, partition_key=session.user_id)

        # Update session timestamp
        await container.patch_item(
            item=session_id,
            partition_key=session.user_id,
            patch_operations=[
                {"op": "set", "path": "/updated_at", "value": now.isoformat()}
            ]
        )

        return Message(
            id=message_id,
            session_id=session_id,
            role=role,
            content=content,
            timestamp=now,
            metadata=metadata or {}
        )

    async def get_messages(
        self,
        session_id: str,
        limit: int = 100
    ) -> list[Message]:
        """Get messages for a session."""
        container = await self._get_container()

        query = """
            SELECT * FROM c
            WHERE c.session_id = @session_id AND c.type = 'message'
            ORDER BY c.timestamp ASC
            OFFSET 0 LIMIT @limit
        """

        items = container.query_items(
            query=query,
            parameters=[
                {"name": "@session_id", "value": session_id},
                {"name": "@limit", "value": limit}
            ]
        )

        messages = []
        async for item in items:
            messages.append(Message(
                id=item["id"],
                session_id=item["session_id"],
                role=item["role"],
                content=item["content"],
                timestamp=datetime.fromisoformat(item["timestamp"]),
                metadata=item.get("metadata", {})
            ))

        return messages

    async def health_check(self) -> bool:
        """Check if Cosmos DB is accessible."""
        try:
            container = await self._get_container()
            # Try to read container properties
            await container.read()
            return True
        except Exception as e:
            logger.warning(f"Cosmos DB health check failed: {e}")
            return False


# =============================================================================
# Factory Function
# =============================================================================

def create_database_service(settings) -> BaseDatabaseService:
    """
    Create database service based on settings.

    Args:
        settings: Configuration settings object

    Returns:
        Database service instance
    """
    from config.settings import DatabaseProvider

    if settings.database_provider == DatabaseProvider.SQLITE:
        return SQLiteService(
            database_path=settings.sqlite.database_path
        )

    elif settings.database_provider == DatabaseProvider.COSMOS_DB:
        return CosmosDBService(
            endpoint=settings.cosmos_db.endpoint,
            key=settings.cosmos_db.key,
            database_name=settings.cosmos_db.database_name,
            container_name=settings.cosmos_db.container_name,
            use_managed_identity=settings.cosmos_db.use_managed_identity
        )

    raise ValueError(f"Unknown database provider: {settings.database_provider}")
