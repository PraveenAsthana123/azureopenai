"""
Real-time Fraud Scoring Function
=================================
Azure Functions for real-time transaction scoring with GenAI explainability
"""

import azure.functions as func
import json
import logging
import os
from datetime import datetime
from typing import Dict, List
import hashlib

from azure.identity import DefaultAzureCredential
from azure.cosmos import CosmosClient
from openai import AzureOpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


# ==============================================================================
# Configuration
# ==============================================================================

class Config:
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    ML_ENDPOINT_URL = os.getenv("ML_ENDPOINT_URL")
    COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")

    ALLOW_THRESHOLD = 30
    REVIEW_THRESHOLD = 70
    BLOCK_THRESHOLD = 70

    GPT_MODEL = "gpt-4o"


# ==============================================================================
# Service Clients
# ==============================================================================

_credential = None
_cosmos_client = None
_openai_client = None


def get_credential():
    global _credential
    if _credential is None:
        _credential = DefaultAzureCredential()
    return _credential


def get_cosmos_container(container_name: str):
    global _cosmos_client
    if _cosmos_client is None:
        _cosmos_client = CosmosClient(
            url=Config.COSMOS_ENDPOINT,
            credential=get_credential()
        )
    database = _cosmos_client.get_database_client("fraud-detection")
    return database.get_container_client(container_name)


def get_openai_client() -> AzureOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AzureOpenAI(
            azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
            azure_ad_token_provider=lambda: get_credential().get_token(
                "https://cognitiveservices.azure.com/.default"
            ).token,
            api_version="2024-06-01"
        )
    return _openai_client


# ==============================================================================
# Feature Enrichment
# ==============================================================================

def enrich_transaction(transaction: Dict) -> Dict:
    """Enrich transaction with customer features and velocity metrics."""
    customer_id = transaction.get("customer_id")

    try:
        container = get_cosmos_container("customer_profiles")
        customer_profile = container.read_item(item=customer_id, partition_key=customer_id)
    except Exception:
        customer_profile = {}

    try:
        velocity_container = get_cosmos_container("velocity_features")
        velocity = velocity_container.read_item(
            item=f"{customer_id}_velocity",
            partition_key=customer_id
        )
    except Exception:
        velocity = {}

    enriched = {
        **transaction,
        "account_age_days": customer_profile.get("account_age_days", 0),
        "avg_transaction_amount": customer_profile.get("avg_transaction_amount", 0),
        "previous_fraud_count": customer_profile.get("previous_fraud_count", 0),
        "txn_count_1h": velocity.get("txn_count_1h", 0),
        "txn_count_24h": velocity.get("txn_count_24h", 0),
        "amount_sum_1h": velocity.get("amount_sum_1h", 0),
    }

    return enriched


# ==============================================================================
# Rules Engine
# ==============================================================================

def apply_rules(transaction: Dict, ml_score: float) -> Dict:
    """Apply business rules on top of ML score."""
    rules_triggered = []
    score_adjustment = 0

    if transaction.get("txn_count_1h", 0) > 10:
        rules_triggered.append({
            "rule_id": "VELOCITY_1H",
            "description": "More than 10 transactions in the last hour",
            "adjustment": 20
        })
        score_adjustment += 20

    if (transaction.get("account_age_days", 365) < 30 and
        transaction.get("amount", 0) > 1000):
        rules_triggered.append({
            "rule_id": "NEW_ACCOUNT_HIGH_VALUE",
            "description": "High-value transaction on new account",
            "adjustment": 25
        })
        score_adjustment += 25

    if transaction.get("previous_fraud_count", 0) > 0:
        rules_triggered.append({
            "rule_id": "FRAUD_HISTORY",
            "description": "Customer has previous fraud incidents",
            "adjustment": 30
        })
        score_adjustment += 30

    final_score = min(100, ml_score + score_adjustment)

    return {
        "final_score": final_score,
        "ml_score": ml_score,
        "rules_adjustment": score_adjustment,
        "rules_triggered": rules_triggered
    }


def make_decision(score: float) -> Dict:
    """Make fraud decision based on risk score."""
    if score < Config.ALLOW_THRESHOLD:
        return {"decision": "ALLOW", "action": "APPROVE_TRANSACTION", "requires_review": False}
    elif score < Config.BLOCK_THRESHOLD:
        return {"decision": "REVIEW", "action": "QUEUE_FOR_REVIEW", "requires_review": True}
    else:
        return {"decision": "BLOCK", "action": "DECLINE_TRANSACTION", "requires_review": True}


# ==============================================================================
# GenAI Explainability
# ==============================================================================

def generate_explanation(transaction: Dict, scoring_result: Dict, rules_result: Dict) -> Dict:
    """Generate human-readable explanation using GPT-4o."""
    client = get_openai_client()

    context = f"""
TRANSACTION: ${transaction.get('amount', 0):.2f} at {transaction.get('merchant_name', 'Unknown')}
RISK SCORE: {rules_result['final_score']}/100
RULES TRIGGERED: {[r['description'] for r in rules_result.get('rules_triggered', [])]}
"""

    prompt = f"""You are a fraud analyst. Based on this transaction, provide a brief JSON analysis:
{context}

Return JSON with: "summary" (2 sentences), "key_concerns" (list of 3), "recommended_actions" (list of 2)"""

    try:
        response = client.chat.completions.create(
            model=Config.GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        return {"explanation": json.loads(response.choices[0].message.content), "generated": True}
    except Exception as e:
        logger.error(f"Explanation generation failed: {e}")
        return {"explanation": None, "generated": False}


# ==============================================================================
# HTTP Endpoints
# ==============================================================================

@app.route(route="score", methods=["POST"])
async def score_transaction_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Real-time transaction scoring endpoint."""
    start_time = datetime.utcnow()

    try:
        transaction = req.get_json()
        enriched = enrich_transaction(transaction)

        # Simulated ML score (in production, call Azure ML endpoint)
        ml_score = 35.0

        rules_result = apply_rules(enriched, ml_score)
        decision = make_decision(rules_result["final_score"])

        explanation = {"explanation": None}
        if decision["decision"] != "ALLOW":
            explanation = generate_explanation(transaction, {"risk_score": ml_score}, rules_result)

        latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        return func.HttpResponse(
            json.dumps({
                "transaction_id": transaction.get("transaction_id"),
                "decision": decision["decision"],
                "risk_score": rules_result["final_score"],
                "latency_ms": round(latency_ms, 2)
            }),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Scoring failed: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e), "decision": "REVIEW"}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="health", methods=["GET"])
async def health_check(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"status": "healthy", "service": "fraud-scoring"}),
        mimetype="application/json"
    )
