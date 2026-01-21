"""
Shared configuration for all backend services
Loads from environment variables or Azure Key Vault
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class AzureOpenAIConfig:
    """Azure OpenAI configuration"""
    endpoint: str
    api_key: str
    api_version: str = "2024-02-01"
    chat_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-large"


@dataclass
class AzureSearchConfig:
    """Azure AI Search configuration"""
    endpoint: str
    api_key: str
    index_name: str = "documents"
    semantic_config: str = "default"


@dataclass
class CosmosDBConfig:
    """Cosmos DB configuration"""
    endpoint: str
    key: str
    database_name: str = "copilot-db"
    connection_string: Optional[str] = None


@dataclass
class StorageConfig:
    """Azure Blob Storage configuration"""
    connection_string: str
    documents_container: str = "documents"
    processed_container: str = "processed"
    embeddings_container: str = "embeddings"


@dataclass
class DocumentIntelligenceConfig:
    """Azure Document Intelligence configuration"""
    endpoint: str
    api_key: str


@dataclass
class ComputerVisionConfig:
    """Azure Computer Vision configuration"""
    endpoint: str
    api_key: str


@dataclass
class ContentSafetyConfig:
    """Azure Content Safety configuration"""
    endpoint: str
    api_key: str


@dataclass
class AppConfig:
    """Main application configuration"""
    environment: str
    openai: AzureOpenAIConfig
    search: AzureSearchConfig
    cosmos: CosmosDBConfig
    storage: StorageConfig
    document_intelligence: DocumentIntelligenceConfig
    computer_vision: ComputerVisionConfig
    content_safety: ContentSafetyConfig

    # RAG Configuration
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_tokens: int = 4000
    temperature: float = 0.1
    top_k: int = 10

    # Monitoring
    app_insights_connection_string: Optional[str] = None


def load_config() -> AppConfig:
    """Load configuration from environment variables"""
    return AppConfig(
        environment=os.environ.get("ENVIRONMENT", "dev"),

        openai=AzureOpenAIConfig(
            endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
            api_key=os.environ.get("AZURE_OPENAI_KEY", ""),
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-01"),
            chat_model=os.environ.get("CHAT_MODEL", "gpt-4o"),
            embedding_model=os.environ.get("EMBEDDING_MODEL", "text-embedding-3-large")
        ),

        search=AzureSearchConfig(
            endpoint=os.environ.get("AZURE_SEARCH_ENDPOINT", ""),
            api_key=os.environ.get("AZURE_SEARCH_KEY", ""),
            index_name=os.environ.get("SEARCH_INDEX_NAME", "documents"),
            semantic_config=os.environ.get("SEARCH_SEMANTIC_CONFIG", "default")
        ),

        cosmos=CosmosDBConfig(
            endpoint=os.environ.get("COSMOS_ENDPOINT", ""),
            key=os.environ.get("COSMOS_KEY", ""),
            database_name=os.environ.get("COSMOS_DATABASE", "copilot-db"),
            connection_string=os.environ.get("COSMOS_CONNECTION_STRING")
        ),

        storage=StorageConfig(
            connection_string=os.environ.get("AZURE_STORAGE_CONNECTION_STRING", ""),
            documents_container=os.environ.get("DOCUMENTS_CONTAINER", "documents"),
            processed_container=os.environ.get("PROCESSED_CONTAINER", "processed"),
            embeddings_container=os.environ.get("EMBEDDINGS_CONTAINER", "embeddings")
        ),

        document_intelligence=DocumentIntelligenceConfig(
            endpoint=os.environ.get("DOC_INTELLIGENCE_ENDPOINT", ""),
            api_key=os.environ.get("DOC_INTELLIGENCE_KEY", "")
        ),

        computer_vision=ComputerVisionConfig(
            endpoint=os.environ.get("COMPUTER_VISION_ENDPOINT", ""),
            api_key=os.environ.get("COMPUTER_VISION_KEY", "")
        ),

        content_safety=ContentSafetyConfig(
            endpoint=os.environ.get("CONTENT_SAFETY_ENDPOINT", ""),
            api_key=os.environ.get("CONTENT_SAFETY_KEY", "")
        ),

        chunk_size=int(os.environ.get("CHUNK_SIZE", "1000")),
        chunk_overlap=int(os.environ.get("CHUNK_OVERLAP", "200")),
        max_tokens=int(os.environ.get("MAX_TOKENS", "4000")),
        temperature=float(os.environ.get("TEMPERATURE", "0.1")),
        top_k=int(os.environ.get("TOP_K", "10")),

        app_insights_connection_string=os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")
    )


# Global config instance
config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get or create config instance"""
    global config
    if config is None:
        config = load_config()
    return config
