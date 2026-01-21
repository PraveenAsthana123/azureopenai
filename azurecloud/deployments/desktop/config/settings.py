"""
Desktop RAG Platform Configuration.

Supports multiple deployment modes:
- LOCAL: Full local deployment with Ollama + ChromaDB + SQLite
- HYBRID: Local compute with Azure services
- AZURE: Full Azure services (same as cloud but local API)

Switch modes via environment variables or config files.
"""

import os
from enum import Enum
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class DeploymentMode(str, Enum):
    """Deployment mode options."""
    LOCAL = "local"      # Full local - Ollama, ChromaDB, SQLite
    HYBRID = "hybrid"    # Mixed - Azure OpenAI + local vector/db
    AZURE = "azure"      # Full Azure services


class LLMProvider(str, Enum):
    """LLM provider options."""
    OLLAMA = "ollama"
    AZURE_OPENAI = "azure_openai"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"  # Claude models


class VectorDBProvider(str, Enum):
    """Vector database provider options."""
    CHROMADB = "chromadb"
    AZURE_SEARCH = "azure_search"
    QDRANT = "qdrant"


class DatabaseProvider(str, Enum):
    """Database provider options."""
    SQLITE = "sqlite"
    COSMOS_DB = "cosmos_db"
    POSTGRESQL = "postgresql"


class StorageProvider(str, Enum):
    """Storage provider options."""
    LOCAL = "local"
    AZURE_BLOB = "azure_blob"
    S3 = "s3"


# =============================================================================
# Provider Settings
# =============================================================================

class OllamaSettings(BaseModel):
    """Ollama local LLM settings."""
    base_url: str = "http://localhost:11434"
    model: str = "llama3.2"  # or "mistral", "phi3", etc.
    embedding_model: str = "nomic-embed-text"
    timeout: int = 120
    num_ctx: int = 4096


class AzureOpenAISettings(BaseModel):
    """Azure OpenAI settings."""
    endpoint: str = ""
    api_key: Optional[str] = None  # Use managed identity if None
    api_version: str = "2024-02-15-preview"
    chat_deployment: str = "gpt-4o-mini"
    embedding_deployment: str = "text-embedding-3-large"
    use_managed_identity: bool = True


class OpenAISettings(BaseModel):
    """OpenAI API settings."""
    api_key: str = ""
    model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"


class AnthropicSettings(BaseModel):
    """Anthropic Claude API settings."""
    api_key: str = ""
    model: str = "claude-sonnet-4-20250514"
    timeout: int = 120
    # For embeddings, use a separate provider (Claude doesn't have embeddings)
    embedding_provider: str = "azure_openai"  # or "openai", "ollama"


class ChromaDBSettings(BaseModel):
    """ChromaDB local vector store settings."""
    persist_directory: str = "./data/chromadb"
    collection_name: str = "rag_documents"
    embedding_function: str = "default"  # or "ollama", "openai"


class AzureSearchSettings(BaseModel):
    """Azure AI Search settings."""
    endpoint: str = ""
    api_key: Optional[str] = None
    index_name: str = "rag-multimodal-index"
    use_managed_identity: bool = True
    semantic_config: str = "default"


class SQLiteSettings(BaseModel):
    """SQLite local database settings."""
    database_path: str = "./data/rag.db"
    echo: bool = False


class CosmosDBSettings(BaseModel):
    """Cosmos DB settings."""
    endpoint: str = ""
    key: Optional[str] = None
    database_name: str = "rag_platform"
    container_name: str = "conversations"
    use_managed_identity: bool = True


class LocalStorageSettings(BaseModel):
    """Local file storage settings."""
    base_path: str = "./data/documents"
    processed_path: str = "./data/processed"
    max_file_size_mb: int = 100


class AzureBlobSettings(BaseModel):
    """Azure Blob Storage settings."""
    connection_string: Optional[str] = None
    account_url: str = ""
    container_name: str = "documents"
    use_managed_identity: bool = True


# =============================================================================
# Main Settings
# =============================================================================

class Settings(BaseSettings):
    """
    Main application settings.

    Load order:
    1. Default values
    2. Config file (if specified)
    3. Environment variables (highest priority)
    """

    # Deployment mode
    deployment_mode: DeploymentMode = DeploymentMode.LOCAL

    # Provider selection
    llm_provider: LLMProvider = LLMProvider.OLLAMA
    vector_db_provider: VectorDBProvider = VectorDBProvider.CHROMADB
    database_provider: DatabaseProvider = DatabaseProvider.SQLITE
    storage_provider: StorageProvider = StorageProvider.LOCAL

    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: Optional[str] = None  # Optional API key for local auth
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    # Provider configurations
    ollama: OllamaSettings = OllamaSettings()
    azure_openai: AzureOpenAISettings = AzureOpenAISettings()
    openai: OpenAISettings = OpenAISettings()
    anthropic: AnthropicSettings = AnthropicSettings()
    chromadb: ChromaDBSettings = ChromaDBSettings()
    azure_search: AzureSearchSettings = AzureSearchSettings()
    sqlite: SQLiteSettings = SQLiteSettings()
    cosmos_db: CosmosDBSettings = CosmosDBSettings()
    local_storage: LocalStorageSettings = LocalStorageSettings()
    azure_blob: AzureBlobSettings = AzureBlobSettings()

    # RAG settings
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k: int = 5
    min_relevance_score: float = 0.5

    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None

    class Config:
        env_prefix = "RAG_"
        env_nested_delimiter = "__"
        env_file = ".env"
        env_file_encoding = "utf-8"

    def get_llm_settings(self):
        """Get settings for the configured LLM provider."""
        if self.llm_provider == LLMProvider.OLLAMA:
            return self.ollama
        elif self.llm_provider == LLMProvider.AZURE_OPENAI:
            return self.azure_openai
        elif self.llm_provider == LLMProvider.OPENAI:
            return self.openai
        elif self.llm_provider == LLMProvider.ANTHROPIC:
            return self.anthropic

    def get_vector_db_settings(self):
        """Get settings for the configured vector DB provider."""
        if self.vector_db_provider == VectorDBProvider.CHROMADB:
            return self.chromadb
        elif self.vector_db_provider == VectorDBProvider.AZURE_SEARCH:
            return self.azure_search

    def get_database_settings(self):
        """Get settings for the configured database provider."""
        if self.database_provider == DatabaseProvider.SQLITE:
            return self.sqlite
        elif self.database_provider == DatabaseProvider.COSMOS_DB:
            return self.cosmos_db

    def get_storage_settings(self):
        """Get settings for the configured storage provider."""
        if self.storage_provider == StorageProvider.LOCAL:
            return self.local_storage
        elif self.storage_provider == StorageProvider.AZURE_BLOB:
            return self.azure_blob


# =============================================================================
# Preset Configurations
# =============================================================================

def get_local_config() -> Settings:
    """Get configuration for full local deployment."""
    return Settings(
        deployment_mode=DeploymentMode.LOCAL,
        llm_provider=LLMProvider.OLLAMA,
        vector_db_provider=VectorDBProvider.CHROMADB,
        database_provider=DatabaseProvider.SQLITE,
        storage_provider=StorageProvider.LOCAL,
    )


def get_hybrid_config() -> Settings:
    """Get configuration for hybrid deployment (Azure LLM + local storage)."""
    return Settings(
        deployment_mode=DeploymentMode.HYBRID,
        llm_provider=LLMProvider.AZURE_OPENAI,
        vector_db_provider=VectorDBProvider.CHROMADB,
        database_provider=DatabaseProvider.SQLITE,
        storage_provider=StorageProvider.LOCAL,
        azure_openai=AzureOpenAISettings(
            endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            use_managed_identity=False,  # Use API key for desktop
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        ),
    )


def get_azure_config() -> Settings:
    """Get configuration for full Azure services."""
    return Settings(
        deployment_mode=DeploymentMode.AZURE,
        llm_provider=LLMProvider.AZURE_OPENAI,
        vector_db_provider=VectorDBProvider.AZURE_SEARCH,
        database_provider=DatabaseProvider.COSMOS_DB,
        storage_provider=StorageProvider.AZURE_BLOB,
        azure_openai=AzureOpenAISettings(
            endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        ),
        azure_search=AzureSearchSettings(
            endpoint=os.getenv("AZURE_SEARCH_ENDPOINT", ""),
            api_key=os.getenv("AZURE_SEARCH_API_KEY"),
        ),
        cosmos_db=CosmosDBSettings(
            endpoint=os.getenv("COSMOS_ENDPOINT", ""),
            key=os.getenv("COSMOS_KEY"),
        ),
        azure_blob=AzureBlobSettings(
            account_url=os.getenv("AZURE_STORAGE_ACCOUNT_URL", ""),
        ),
    )


def load_settings() -> Settings:
    """Load settings based on deployment mode."""
    mode = os.getenv("RAG_DEPLOYMENT_MODE", "local").lower()

    if mode == "local":
        return get_local_config()
    elif mode == "hybrid":
        return get_hybrid_config()
    elif mode == "azure":
        return get_azure_config()
    else:
        return Settings()


# Global settings instance
settings = load_settings()
