"""
Banking CRM Solution - Azure Functions
===================================================
AI-powered banking CRM with customer 360, next-best-action,
churn prediction, and KYC/AML compliance
"""

import azure.functions as func
import logging
import json
import os
from datetime import datetime
from typing import Optional
import hashlib

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.cosmos import CosmosClient
from openai import AzureOpenAI

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Azure Function App
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# ==============================================================================
# Configuration
# ==============================================================================

class Config:
    """Application configuration from environment variables."""

    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
    COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
    KEY_VAULT_URL = os.getenv("KEY_VAULT_URL")
    ML_ENDPOINT = os.getenv("ML_ENDPOINT")
    REDIS_HOST = os.getenv("REDIS_HOST")

    # Model configurations
    GPT_MODEL = "gpt-4o"
    EMBEDDING_MODEL = "text-embedding-ada-002"
    SEARCH_INDEX = "customer-knowledge-index"

    # Banking CRM parameters
    CHURN_THRESHOLD = 0.65
    AML_RISK_THRESHOLD = 0.70
    CROSS_SELL_MIN_SCORE = 0.50
    MAX_TOKENS = 4096
    TEMPERATURE = 0.3


# ==============================================================================
# Service Clients (Lazy Initialization)
# ==============================================================================

_credential = None
_openai_client = None
_search_client = None
_cosmos_client = None
_keyvault_client = None


def get_credential():
    """Get Azure credential using Managed Identity."""
    global _credential
    if _credential is None:
        _credential = DefaultAzureCredential()
    return _credential


def get_openai_client() -> AzureOpenAI:
    """Get Azure OpenAI client."""
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


def get_search_client() -> SearchClient:
    """Get Azure AI Search client."""
    global _search_client
    if _search_client is None:
        _search_client = SearchClient(
            endpoint=Config.AZURE_SEARCH_ENDPOINT,
            index_name=Config.SEARCH_INDEX,
            credential=get_credential()
        )
    return _search_client


def get_cosmos_container(container_name: str):
    """Get Cosmos DB container client."""
    global _cosmos_client
    if _cosmos_client is None:
        _cosmos_client = CosmosClient(
            url=Config.COSMOS_ENDPOINT,
            credential=get_credential()
        )
    database = _cosmos_client.get_database_client("bankingcrm")
    return database.get_container_client(container_name)


def get_keyvault_client() -> SecretClient:
    """Get Azure Key Vault client."""
    global _keyvault_client
    if _keyvault_client is None:
        _keyvault_client = SecretClient(
            vault_url=Config.KEY_VAULT_URL,
            credential=get_credential()
        )
    return _keyvault_client


# ==============================================================================
# Core Domain Functions
# ==============================================================================

def generate_embedding(text: str) -> list[float]:
    """Generate embedding vector for text using Azure OpenAI."""
    client = get_openai_client()

    response = client.embeddings.create(
        input=text,
        model=Config.EMBEDDING_MODEL
    )

    return response.data[0].embedding


def get_customer_360(customer_id: str) -> dict:
    """
    Build unified customer 360 view from Cosmos DB.

    Aggregates data across deposits, loans, credit cards, investments,
    and interaction history into a single comprehensive customer profile.

    Args:
        customer_id: Unique customer identifier

    Returns:
        Unified customer profile dictionary
    """
    logger.info(f"Building customer 360 for: {customer_id}")

    # Retrieve core customer profile
    profile_container = get_cosmos_container("customers")
    profile = profile_container.read_item(item=customer_id, partition_key=customer_id)

    # Retrieve deposit accounts
    accounts_container = get_cosmos_container("accounts")
    deposits = list(accounts_container.query_items(
        query="SELECT * FROM c WHERE c.customerId = @cid AND c.accountType IN ('savings', 'checking', 'fixed_deposit')",
        parameters=[{"name": "@cid", "value": customer_id}],
        enable_cross_partition_query=True
    ))

    # Retrieve loan accounts
    loans = list(accounts_container.query_items(
        query="SELECT * FROM c WHERE c.customerId = @cid AND c.accountType IN ('mortgage', 'personal_loan', 'auto_loan')",
        parameters=[{"name": "@cid", "value": customer_id}],
        enable_cross_partition_query=True
    ))

    # Retrieve credit card accounts
    cards = list(accounts_container.query_items(
        query="SELECT * FROM c WHERE c.customerId = @cid AND c.accountType = 'credit_card'",
        parameters=[{"name": "@cid", "value": customer_id}],
        enable_cross_partition_query=True
    ))

    # Retrieve investment portfolios
    investments_container = get_cosmos_container("investments")
    investments = list(investments_container.query_items(
        query="SELECT * FROM c WHERE c.customerId = @cid",
        parameters=[{"name": "@cid", "value": customer_id}],
        enable_cross_partition_query=True
    ))

    # Retrieve recent interactions
    interactions_container = get_cosmos_container("interactions")
    interactions = list(interactions_container.query_items(
        query="SELECT TOP 20 * FROM c WHERE c.customerId = @cid ORDER BY c.timestamp DESC",
        parameters=[{"name": "@cid", "value": customer_id}],
        enable_cross_partition_query=True
    ))

    # Calculate aggregated metrics
    total_deposits = sum(a.get("balance", 0) for a in deposits)
    total_loan_outstanding = sum(l.get("outstandingBalance", 0) for l in loans)
    total_card_balance = sum(c.get("currentBalance", 0) for c in cards)
    total_investment_value = sum(i.get("marketValue", 0) for i in investments)
    total_relationship_value = total_deposits + total_investment_value - total_loan_outstanding - total_card_balance

    customer_360 = {
        "customerId": customer_id,
        "profile": {
            "name": profile.get("name"),
            "segment": profile.get("segment"),
            "tier": profile.get("tier"),
            "relationshipStartDate": profile.get("relationshipStartDate"),
            "rmAssigned": profile.get("rmAssigned"),
            "kycStatus": profile.get("kycStatus"),
            "riskRating": profile.get("riskRating")
        },
        "deposits": {
            "accounts": deposits,
            "totalBalance": total_deposits
        },
        "loans": {
            "accounts": loans,
            "totalOutstanding": total_loan_outstanding
        },
        "creditCards": {
            "accounts": cards,
            "totalBalance": total_card_balance
        },
        "investments": {
            "portfolios": investments,
            "totalMarketValue": total_investment_value
        },
        "relationshipValue": total_relationship_value,
        "recentInteractions": interactions[:10],
        "generatedAt": datetime.utcnow().isoformat()
    }

    return customer_360


def recommend_next_best_action(customer_id: str, customer_data: dict) -> dict:
    """
    AI-driven next-best-action recommendation using customer profile,
    transaction patterns, and life events.

    Args:
        customer_id: Unique customer identifier
        customer_data: Customer 360 data

    Returns:
        Next-best-action recommendations with rationale
    """
    logger.info(f"Generating NBA for customer: {customer_id}")

    client = get_openai_client()

    # Search for similar customer patterns
    profile_summary = json.dumps({
        "segment": customer_data.get("profile", {}).get("segment"),
        "tier": customer_data.get("profile", {}).get("tier"),
        "relationshipValue": customer_data.get("relationshipValue"),
        "depositBalance": customer_data.get("deposits", {}).get("totalBalance"),
        "loanOutstanding": customer_data.get("loans", {}).get("totalOutstanding"),
        "investmentValue": customer_data.get("investments", {}).get("totalMarketValue")
    })

    query_vector = generate_embedding(f"customer profile banking recommendations {profile_summary}")
    vector_query = VectorizedQuery(
        vector=query_vector,
        k_nearest_neighbors=5,
        fields="contentVector"
    )

    search_results = get_search_client().search(
        search_text=f"next best action {customer_data.get('profile', {}).get('segment')}",
        vector_queries=[vector_query],
        top=5,
        select=["id", "content", "title", "source"]
    )

    context_docs = [result["content"] for result in search_results]

    system_prompt = """You are an AI banking relationship advisor. Based on the customer data
and knowledge base context, recommend the top 3 next-best-actions for this customer.

For each recommendation provide:
1. Action type (product offer, service improvement, engagement, retention)
2. Specific recommendation
3. Rationale based on customer data
4. Expected impact (revenue, satisfaction, retention)
5. Urgency level (high, medium, low)
6. Suggested channel (branch, phone, email, mobile app)

Return response as valid JSON with key "recommendations" containing an array."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Customer Data:\n{json.dumps(customer_data, default=str)}\n\nContext:\n{chr(10).join(context_docs[:3])}"}
    ]

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=messages,
        max_tokens=Config.MAX_TOKENS,
        temperature=Config.TEMPERATURE,
        response_format={"type": "json_object"}
    )

    recommendations = json.loads(response.choices[0].message.content)

    return {
        "customerId": customer_id,
        "recommendations": recommendations.get("recommendations", []),
        "modelVersion": response.model,
        "generatedAt": datetime.utcnow().isoformat(),
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
    }


def predict_churn(customer_id: str, customer_data: dict) -> dict:
    """
    Churn risk scoring with contributing factors and retention recommendations.

    Analyzes customer behavior patterns, engagement metrics, and account activity
    to predict likelihood of customer attrition.

    Args:
        customer_id: Unique customer identifier
        customer_data: Customer 360 data

    Returns:
        Churn prediction with risk score, factors, and retention actions
    """
    logger.info(f"Predicting churn for customer: {customer_id}")

    client = get_openai_client()

    system_prompt = """You are a banking customer churn prediction specialist. Analyze the
customer data and provide a churn risk assessment.

Return a JSON response with:
1. "riskScore": float between 0.0 (no risk) and 1.0 (certain churn)
2. "riskLevel": "low", "medium", "high", or "critical"
3. "contributingFactors": array of factors with name, impact (positive/negative), and weight
4. "earlyWarningSignals": array of detected warning signals
5. "retentionRecommendations": array of specific retention actions with priority
6. "predictedTimeframe": estimated time until potential churn
7. "confidenceScore": model confidence in prediction"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Customer Data:\n{json.dumps(customer_data, default=str)}"}
    ]

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=messages,
        max_tokens=Config.MAX_TOKENS,
        temperature=0.2,
        response_format={"type": "json_object"}
    )

    prediction = json.loads(response.choices[0].message.content)
    risk_score = prediction.get("riskScore", 0.0)

    return {
        "customerId": customer_id,
        "churnPrediction": prediction,
        "isHighRisk": risk_score >= Config.CHURN_THRESHOLD,
        "alertTriggered": risk_score >= Config.CHURN_THRESHOLD,
        "generatedAt": datetime.utcnow().isoformat()
    }


def screen_kyc_aml(customer_id: str, transaction_data: dict) -> dict:
    """
    KYC/AML screening using AI for suspicious activity detection.

    Analyzes transaction patterns, counterparty information, and behavioral
    anomalies to identify potential money laundering or compliance violations.

    Args:
        customer_id: Unique customer identifier
        transaction_data: Transaction details and history to screen

    Returns:
        KYC/AML screening results with risk flags and recommended actions
    """
    logger.info(f"Running KYC/AML screening for customer: {customer_id}")

    client = get_openai_client()

    # Retrieve customer KYC records
    kyc_container = get_cosmos_container("kycRecords")
    kyc_records = list(kyc_container.query_items(
        query="SELECT * FROM c WHERE c.customerId = @cid ORDER BY c.screeningDate DESC",
        parameters=[{"name": "@cid", "value": customer_id}],
        enable_cross_partition_query=True
    ))

    system_prompt = """You are a banking compliance AI specialist for KYC/AML screening.
Analyze the transaction data and customer history for potential compliance issues.

Return a JSON response with:
1. "overallRiskScore": float between 0.0 and 1.0
2. "riskCategory": "low", "medium", "high", or "critical"
3. "flags": array of identified risk flags with type, description, and severity
4. "suspiciousPatterns": array of detected suspicious activity patterns
5. "sanctionsScreening": results of sanctions list matching
6. "pepScreening": politically exposed persons check results
7. "recommendedActions": array of compliance actions (escalate, investigate, clear, block)
8. "regulatoryReferences": applicable regulations (e.g., BSA, AML Directive)
9. "narrativeSummary": plain-language summary for compliance officers

IMPORTANT: Be thorough but avoid false positives. Flag only genuine concerns."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Customer ID: {customer_id}\nKYC History: {json.dumps(kyc_records[:5], default=str)}\nTransaction Data: {json.dumps(transaction_data, default=str)}"}
    ]

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=messages,
        max_tokens=Config.MAX_TOKENS,
        temperature=0.1,
        response_format={"type": "json_object"}
    )

    screening_result = json.loads(response.choices[0].message.content)
    risk_score = screening_result.get("overallRiskScore", 0.0)

    # Log screening for audit trail
    audit_container = get_cosmos_container("auditLog")
    audit_record = {
        "id": hashlib.md5(f"{customer_id}-kyc-{datetime.utcnow().isoformat()}".encode()).hexdigest(),
        "customerId": customer_id,
        "screeningType": "KYC_AML",
        "riskScore": risk_score,
        "riskCategory": screening_result.get("riskCategory"),
        "flagCount": len(screening_result.get("flags", [])),
        "timestamp": datetime.utcnow().isoformat(),
        "modelVersion": response.model
    }
    audit_container.create_item(body=audit_record)

    return {
        "customerId": customer_id,
        "screeningResult": screening_result,
        "requiresEscalation": risk_score >= Config.AML_RISK_THRESHOLD,
        "auditRecordId": audit_record["id"],
        "generatedAt": datetime.utcnow().isoformat()
    }


def generate_rm_insights(customer_id: str) -> dict:
    """
    RM copilot generating relationship manager briefing with talking points.

    Produces a comprehensive briefing for the relationship manager including
    customer summary, recent activity, opportunities, risks, and suggested
    conversation topics.

    Args:
        customer_id: Unique customer identifier

    Returns:
        RM briefing with talking points, opportunities, and action items
    """
    logger.info(f"Generating RM insights for customer: {customer_id}")

    # Build customer 360 first
    customer_data = get_customer_360(customer_id)

    client = get_openai_client()

    system_prompt = """You are an AI copilot for banking relationship managers. Generate a
comprehensive customer briefing document for an upcoming client meeting.

Return a JSON response with:
1. "executiveSummary": 2-3 sentence overview of the customer relationship
2. "relationshipHealth": score from 1-10 with explanation
3. "recentActivity": summary of notable recent transactions and interactions
4. "opportunities": array of business opportunities with estimated value
5. "risks": array of relationship risks to address
6. "talkingPoints": array of 5-7 suggested conversation topics with context
7. "competitiveIntel": any known competitive threats or market context
8. "actionItems": prioritized list of follow-up actions for the RM
9. "personalNotes": relevant personal information for rapport building
10. "nextMeetingAgenda": suggested agenda items for the meeting"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Customer Data:\n{json.dumps(customer_data, default=str)}"}
    ]

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=messages,
        max_tokens=Config.MAX_TOKENS,
        temperature=Config.TEMPERATURE,
        response_format={"type": "json_object"}
    )

    insights = json.loads(response.choices[0].message.content)

    return {
        "customerId": customer_id,
        "rmInsights": insights,
        "customerSegment": customer_data.get("profile", {}).get("segment"),
        "relationshipValue": customer_data.get("relationshipValue"),
        "generatedAt": datetime.utcnow().isoformat()
    }


def score_cross_sell_propensity(customer_id: str, customer_data: dict) -> dict:
    """
    Product propensity scoring for cross-sell and upsell opportunities.

    Evaluates the customer's likelihood to purchase additional banking products
    based on their profile, current portfolio, and peer group behavior.

    Args:
        customer_id: Unique customer identifier
        customer_data: Customer 360 data

    Returns:
        Product propensity scores with recommendations
    """
    logger.info(f"Scoring cross-sell propensity for customer: {customer_id}")

    client = get_openai_client()

    # Determine current product holdings
    current_products = []
    if customer_data.get("deposits", {}).get("accounts"):
        current_products.extend([a.get("accountType") for a in customer_data["deposits"]["accounts"]])
    if customer_data.get("loans", {}).get("accounts"):
        current_products.extend([l.get("accountType") for l in customer_data["loans"]["accounts"]])
    if customer_data.get("creditCards", {}).get("accounts"):
        current_products.append("credit_card")
    if customer_data.get("investments", {}).get("portfolios"):
        current_products.append("investments")

    system_prompt = """You are a banking product recommendation specialist. Analyze the
customer data and current product holdings to score cross-sell and upsell propensity.

Products to evaluate:
- Premium savings account
- Fixed deposit / CD
- Personal loan
- Mortgage / Home equity
- Credit card upgrade
- Investment advisory
- Insurance (life, property)
- Wealth management
- Business banking (if applicable)
- Digital payment services

Return a JSON response with:
1. "productScores": array of products with name, propensityScore (0.0-1.0), rationale, and expectedRevenue
2. "topRecommendation": the single best cross-sell opportunity
3. "bundleOpportunity": suggested product bundle with combined value proposition
4. "timingSignals": indicators suggesting optimal timing for offers
5. "channelPreference": recommended channel for each product offer"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Customer Data:\n{json.dumps(customer_data, default=str)}\nCurrent Products: {json.dumps(current_products)}"}
    ]

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=messages,
        max_tokens=Config.MAX_TOKENS,
        temperature=Config.TEMPERATURE,
        response_format={"type": "json_object"}
    )

    propensity = json.loads(response.choices[0].message.content)

    # Filter to actionable scores
    actionable = [
        p for p in propensity.get("productScores", [])
        if p.get("propensityScore", 0) >= Config.CROSS_SELL_MIN_SCORE
    ]

    return {
        "customerId": customer_id,
        "currentProducts": current_products,
        "propensityScores": propensity.get("productScores", []),
        "actionableOffers": actionable,
        "topRecommendation": propensity.get("topRecommendation"),
        "bundleOpportunity": propensity.get("bundleOpportunity"),
        "generatedAt": datetime.utcnow().isoformat()
    }


# ==============================================================================
# HTTP Endpoints
# ==============================================================================

@app.route(route="customer-360", methods=["POST"])
async def customer_360_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Unified customer 360 view endpoint.

    Request Body:
    {
        "customer_id": "CUST-001"
    }
    """
    try:
        req_body = req.get_json()
        customer_id = req_body.get("customer_id")

        if not customer_id:
            return func.HttpResponse(
                json.dumps({"error": "customer_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Customer 360 request for: {customer_id}")

        result = get_customer_360(customer_id)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error building customer 360: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="next-best-action", methods=["POST"])
async def next_best_action_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Next-best-action recommendation endpoint.

    Request Body:
    {
        "customer_id": "CUST-001",
        "customer_data": { ... }  // optional, will fetch if not provided
    }
    """
    try:
        req_body = req.get_json()
        customer_id = req_body.get("customer_id")
        customer_data = req_body.get("customer_data")

        if not customer_id:
            return func.HttpResponse(
                json.dumps({"error": "customer_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        if not customer_data:
            customer_data = get_customer_360(customer_id)

        logger.info(f"NBA request for: {customer_id}")

        result = recommend_next_best_action(customer_id, customer_data)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error generating NBA: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="churn-predict", methods=["POST"])
async def churn_predict_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Churn prediction endpoint.

    Request Body:
    {
        "customer_id": "CUST-001",
        "customer_data": { ... }  // optional
    }
    """
    try:
        req_body = req.get_json()
        customer_id = req_body.get("customer_id")
        customer_data = req_body.get("customer_data")

        if not customer_id:
            return func.HttpResponse(
                json.dumps({"error": "customer_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        if not customer_data:
            customer_data = get_customer_360(customer_id)

        logger.info(f"Churn prediction request for: {customer_id}")

        result = predict_churn(customer_id, customer_data)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error predicting churn: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="kyc-screen", methods=["POST"])
async def kyc_screen_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    KYC/AML screening endpoint.

    Request Body:
    {
        "customer_id": "CUST-001",
        "transaction_data": {
            "transactions": [...],
            "period": "2024-01-01/2024-12-31"
        }
    }
    """
    try:
        req_body = req.get_json()
        customer_id = req_body.get("customer_id")
        transaction_data = req_body.get("transaction_data", {})

        if not customer_id:
            return func.HttpResponse(
                json.dumps({"error": "customer_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"KYC/AML screening request for: {customer_id}")

        result = screen_kyc_aml(customer_id, transaction_data)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error in KYC/AML screening: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="rm-insights", methods=["POST"])
async def rm_insights_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    RM copilot insights endpoint.

    Request Body:
    {
        "customer_id": "CUST-001"
    }
    """
    try:
        req_body = req.get_json()
        customer_id = req_body.get("customer_id")

        if not customer_id:
            return func.HttpResponse(
                json.dumps({"error": "customer_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"RM insights request for: {customer_id}")

        result = generate_rm_insights(customer_id)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error generating RM insights: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="cross-sell", methods=["POST"])
async def cross_sell_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Cross-sell propensity scoring endpoint.

    Request Body:
    {
        "customer_id": "CUST-001",
        "customer_data": { ... }  // optional
    }
    """
    try:
        req_body = req.get_json()
        customer_id = req_body.get("customer_id")
        customer_data = req_body.get("customer_data")

        if not customer_id:
            return func.HttpResponse(
                json.dumps({"error": "customer_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        if not customer_data:
            customer_data = get_customer_360(customer_id)

        logger.info(f"Cross-sell scoring request for: {customer_id}")

        result = score_cross_sell_propensity(customer_id, customer_data)

        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error scoring cross-sell: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="health", methods=["GET"])
async def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint."""
    return func.HttpResponse(
        json.dumps({
            "status": "healthy",
            "service": "banking-crm-solution",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "endpoints": [
                "customer-360",
                "next-best-action",
                "churn-predict",
                "kyc-screen",
                "rm-insights",
                "cross-sell"
            ]
        }),
        mimetype="application/json"
    )


# ==============================================================================
# Event Hub Trigger for Real-Time Customer Event Processing
# ==============================================================================

@app.function_name(name="CustomerEventProcessor")
@app.event_hub_message_trigger(
    arg_name="event",
    event_hub_name="customer-events",
    connection="EVENT_HUB_CONNECTION"
)
async def customer_event_processor(event: func.EventHubEvent):
    """
    Real-time customer event processing trigger.

    Processes events such as large transactions, account changes, service
    interactions, and behavioral signals to update risk scores and trigger
    proactive outreach.
    """
    try:
        event_body = json.loads(event.get_body().decode("utf-8"))
        event_type = event_body.get("eventType")
        customer_id = event_body.get("customerId")
        event_data = event_body.get("data", {})

        logger.info(f"Processing customer event: {event_type} for {customer_id}")

        # Route event to appropriate handler
        if event_type == "large_transaction":
            # Screen for AML compliance
            screening = screen_kyc_aml(customer_id, {"transactions": [event_data]})
            if screening.get("requiresEscalation"):
                logger.warning(f"AML escalation triggered for customer: {customer_id}")
                # Store alert for compliance team
                alerts_container = get_cosmos_container("complianceAlerts")
                alerts_container.create_item(body={
                    "id": hashlib.md5(f"{customer_id}-alert-{datetime.utcnow().isoformat()}".encode()).hexdigest(),
                    "customerId": customer_id,
                    "alertType": "AML_ESCALATION",
                    "eventType": event_type,
                    "screeningResult": screening,
                    "status": "pending",
                    "createdAt": datetime.utcnow().isoformat()
                })

        elif event_type == "account_closure_request":
            # Trigger churn prediction and retention workflow
            customer_data = get_customer_360(customer_id)
            churn_result = predict_churn(customer_id, customer_data)
            if churn_result.get("isHighRisk"):
                logger.info(f"High churn risk detected, generating retention offer for: {customer_id}")
                nba = recommend_next_best_action(customer_id, customer_data)
                # Store retention case
                retention_container = get_cosmos_container("retentionCases")
                retention_container.create_item(body={
                    "id": hashlib.md5(f"{customer_id}-retention-{datetime.utcnow().isoformat()}".encode()).hexdigest(),
                    "customerId": customer_id,
                    "churnPrediction": churn_result,
                    "retentionActions": nba.get("recommendations", []),
                    "status": "open",
                    "createdAt": datetime.utcnow().isoformat()
                })

        elif event_type == "life_event_detected":
            # Life event triggers cross-sell opportunity
            customer_data = get_customer_360(customer_id)
            cross_sell = score_cross_sell_propensity(customer_id, customer_data)
            if cross_sell.get("actionableOffers"):
                logger.info(f"Cross-sell opportunity detected for: {customer_id}")
                opportunities_container = get_cosmos_container("opportunities")
                opportunities_container.create_item(body={
                    "id": hashlib.md5(f"{customer_id}-opportunity-{datetime.utcnow().isoformat()}".encode()).hexdigest(),
                    "customerId": customer_id,
                    "trigger": event_type,
                    "lifeEvent": event_data.get("eventName"),
                    "offers": cross_sell.get("actionableOffers", []),
                    "topRecommendation": cross_sell.get("topRecommendation"),
                    "status": "new",
                    "createdAt": datetime.utcnow().isoformat()
                })

        elif event_type == "rm_meeting_scheduled":
            # Pre-generate RM briefing
            insights = generate_rm_insights(customer_id)
            briefings_container = get_cosmos_container("rmBriefings")
            briefings_container.create_item(body={
                "id": hashlib.md5(f"{customer_id}-briefing-{datetime.utcnow().isoformat()}".encode()).hexdigest(),
                "customerId": customer_id,
                "meetingDate": event_data.get("meetingDate"),
                "rmId": event_data.get("rmId"),
                "briefing": insights,
                "status": "generated",
                "createdAt": datetime.utcnow().isoformat()
            })
            logger.info(f"RM briefing pre-generated for customer: {customer_id}")

        else:
            logger.info(f"Unhandled event type: {event_type} for customer: {customer_id}")

    except Exception as e:
        logger.error(f"Error processing customer event: {e}", exc_info=True)
        raise
