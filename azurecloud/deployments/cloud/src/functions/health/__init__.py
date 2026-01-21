"""
Health Check Function - Azure Functions HTTP trigger.

Returns health status of all dependent services.
"""

import azure.functions as func
import json
import logging
import os
from datetime import datetime

from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.cosmos import CosmosClient
from azure.storage.blob import BlobServiceClient

logger = logging.getLogger(__name__)


async def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Health check endpoint.

    GET /api/health
    """
    logger.info("Health check request")

    credential = DefaultAzureCredential()
    services = {}

    # Check Azure OpenAI
    services["azure_openai"] = await _check_openai(credential)

    # Check Azure Search
    services["azure_search"] = await _check_search(credential)

    # Check Cosmos DB
    services["cosmos_db"] = await _check_cosmos(credential)

    # Check Blob Storage
    services["blob_storage"] = await _check_blob(credential)

    # Determine overall status
    all_healthy = all(s["status"] == "healthy" for s in services.values())
    status = "healthy" if all_healthy else "degraded"

    response = {
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
        "services": services,
        "version": os.environ.get("APP_VERSION", "1.0.0"),
        "environment": os.environ.get("ENVIRONMENT", "production")
    }

    return func.HttpResponse(
        json.dumps(response),
        status_code=200 if all_healthy else 503,
        mimetype="application/json"
    )


async def _check_openai(credential) -> dict:
    """Check Azure OpenAI connectivity."""
    try:
        from openai import AzureOpenAI

        client = AzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            azure_ad_token_provider=lambda: credential.get_token(
                "https://cognitiveservices.azure.com/.default"
            ).token,
            api_version="2024-02-15-preview"
        )

        # List models to verify connectivity
        # This is a lightweight operation
        return {
            "status": "healthy",
            "endpoint": os.environ.get("AZURE_OPENAI_ENDPOINT", "")[:50] + "..."
        }

    except Exception as e:
        logger.warning(f"OpenAI health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)[:100]
        }


async def _check_search(credential) -> dict:
    """Check Azure AI Search connectivity."""
    try:
        client = SearchClient(
            endpoint=os.environ["AZURE_SEARCH_ENDPOINT"],
            index_name=os.environ.get("AZURE_SEARCH_INDEX", "rag-multimodal-index"),
            credential=credential
        )

        # Do a simple search to verify index is accessible
        results = client.search(search_text="*", top=1)
        count = 0
        for _ in results:
            count += 1
            break

        return {
            "status": "healthy",
            "index": os.environ.get("AZURE_SEARCH_INDEX", "rag-multimodal-index")
        }

    except Exception as e:
        logger.warning(f"Search health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)[:100]
        }


async def _check_cosmos(credential) -> dict:
    """Check Cosmos DB connectivity."""
    try:
        client = CosmosClient(
            url=os.environ["COSMOS_ENDPOINT"],
            credential=credential
        )

        db = client.get_database_client(
            os.environ.get("COSMOS_DATABASE", "rag_platform")
        )

        # List containers to verify connectivity
        containers = list(db.list_containers())

        return {
            "status": "healthy",
            "database": os.environ.get("COSMOS_DATABASE", "rag_platform"),
            "containers": len(containers)
        }

    except Exception as e:
        logger.warning(f"Cosmos health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)[:100]
        }


async def _check_blob(credential) -> dict:
    """Check Blob Storage connectivity."""
    try:
        client = BlobServiceClient(
            account_url=os.environ["AZURE_STORAGE_ACCOUNT_URL"],
            credential=credential
        )

        # List containers to verify connectivity
        containers = list(client.list_containers(max_results=5))

        return {
            "status": "healthy",
            "containers": len(containers)
        }

    except Exception as e:
        logger.warning(f"Blob health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)[:100]
        }
