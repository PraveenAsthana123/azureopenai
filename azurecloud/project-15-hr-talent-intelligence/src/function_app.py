"""
HR Talent Intelligence Platform - Azure Functions
===================================================
AI-powered resume screening, skill gap analysis, internal mobility
matching, and workforce planning for enterprise HR operations.
"""

import azure.functions as func
import logging
import json
import os
from datetime import datetime
from typing import Optional
import hashlib

from azure.identity import DefaultAzureCredential
from azure.cosmos import CosmosClient
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
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

    # Model configurations
    GPT_MODEL = "gpt-4o"
    EMBEDDING_MODEL = "text-embedding-ada-002"
    SEARCH_INDEX = "talent-index"

    # Talent intelligence parameters
    SCREENING_THRESHOLD = 0.65
    MOBILITY_MATCH_THRESHOLD = 0.70
    TOP_K = 10
    MAX_TOKENS = 4096
    TEMPERATURE = 0.4


# ==============================================================================
# Service Clients (Lazy Initialization)
# ==============================================================================

_credential = None
_openai_client = None
_search_client = None
_cosmos_client = None


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
    database = _cosmos_client.get_database_client("talent-intelligence")
    return database.get_container_client(container_name)


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


def screen_resume(resume_text: str, job_requirements: dict) -> dict:
    """
    AI-powered resume screening with scoring and matching.

    Args:
        resume_text: Raw text extracted from the candidate resume
        job_requirements: Job description with required skills, experience, and qualifications

    Returns:
        Screening result with overall score, skill matches, and recommendation
    """
    client = get_openai_client()

    system_prompt = """You are an expert HR talent screening assistant.
Analyze the provided resume against job requirements and produce a structured evaluation.

INSTRUCTIONS:
1. Score the candidate from 0.0 to 1.0 on overall fit
2. Identify matched and missing skills
3. Evaluate experience relevance
4. Assess education and certifications alignment
5. Provide a clear hiring recommendation: STRONG_MATCH, POTENTIAL_MATCH, or NO_MATCH
6. Be objective and avoid any bias related to demographics

Return your analysis as valid JSON with these fields:
- overall_score (float)
- skill_matches (list of matched skills)
- skill_gaps (list of missing required skills)
- experience_score (float)
- education_match (bool)
- recommendation (string)
- summary (string, 2-3 sentence justification)
"""

    user_prompt = f"""RESUME:
{resume_text}

JOB REQUIREMENTS:
Title: {job_requirements.get('title', 'N/A')}
Required Skills: {', '.join(job_requirements.get('required_skills', []))}
Preferred Skills: {', '.join(job_requirements.get('preferred_skills', []))}
Minimum Experience: {job_requirements.get('min_experience_years', 'N/A')} years
Education: {job_requirements.get('education', 'N/A')}
"""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=Config.MAX_TOKENS,
        temperature=0.2,
        response_format={"type": "json_object"}
    )

    screening_result = json.loads(response.choices[0].message.content)
    screening_result["model"] = response.model
    screening_result["usage"] = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens
    }

    return screening_result


def analyze_skill_gaps(employee_skills: list[str], target_role: dict) -> dict:
    """
    Identify skill gaps and recommend learning paths for career development.

    Args:
        employee_skills: List of current employee skills
        target_role: Target role details including required competencies

    Returns:
        Skill gap analysis with learning path recommendations
    """
    client = get_openai_client()

    system_prompt = """You are a career development and skills advisor.
Analyze the gap between an employee's current skills and a target role's requirements.

INSTRUCTIONS:
1. Identify skills the employee already has that match the target role
2. Identify missing skills categorized by priority (critical, important, nice-to-have)
3. Recommend specific learning paths, certifications, or training programs
4. Estimate a realistic timeline for skill acquisition
5. Suggest interim roles or stretch assignments for growth

Return your analysis as valid JSON with these fields:
- matching_skills (list)
- critical_gaps (list of {skill, learning_path, estimated_weeks})
- important_gaps (list of {skill, learning_path, estimated_weeks})
- nice_to_have_gaps (list of {skill, learning_path, estimated_weeks})
- recommended_certifications (list)
- stretch_assignments (list)
- overall_readiness_score (float, 0.0 to 1.0)
- estimated_months_to_ready (int)
- summary (string)
"""

    user_prompt = f"""CURRENT EMPLOYEE SKILLS:
{', '.join(employee_skills)}

TARGET ROLE:
Title: {target_role.get('title', 'N/A')}
Required Skills: {', '.join(target_role.get('required_skills', []))}
Preferred Skills: {', '.join(target_role.get('preferred_skills', []))}
Level: {target_role.get('level', 'N/A')}
Department: {target_role.get('department', 'N/A')}
"""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=Config.MAX_TOKENS,
        temperature=0.3,
        response_format={"type": "json_object"}
    )

    gap_analysis = json.loads(response.choices[0].message.content)
    gap_analysis["usage"] = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens
    }

    return gap_analysis


def match_internal_mobility(employee_profile: dict, open_positions: list[dict]) -> dict:
    """
    Match employees to internal mobility opportunities using AI and vector search.

    Args:
        employee_profile: Employee details including skills, experience, preferences
        open_positions: List of open internal positions to match against

    Returns:
        Ranked list of matching positions with fit scores and justifications
    """
    client = get_openai_client()

    # Build employee summary for embedding
    employee_summary = (
        f"Skills: {', '.join(employee_profile.get('skills', []))}. "
        f"Experience: {employee_profile.get('experience_years', 0)} years. "
        f"Current role: {employee_profile.get('current_role', 'N/A')}. "
        f"Career interests: {', '.join(employee_profile.get('career_interests', []))}."
    )

    # Generate embedding for vector similarity search
    employee_vector = generate_embedding(employee_summary)

    # Search for matching positions in the talent index
    search_client = get_search_client()
    vector_query = VectorizedQuery(
        vector=employee_vector,
        k_nearest_neighbors=Config.TOP_K,
        fields="positionVector"
    )

    results = search_client.search(
        search_text=employee_summary,
        vector_queries=[vector_query],
        top=Config.TOP_K,
        select=["id", "title", "department", "required_skills", "level", "description"]
    )

    candidate_positions = []
    for result in results:
        candidate_positions.append({
            "id": result["id"],
            "title": result.get("title", "Unknown"),
            "department": result.get("department", "Unknown"),
            "required_skills": result.get("required_skills", []),
            "level": result.get("level", "N/A"),
            "description": result.get("description", ""),
            "search_score": result["@search.score"]
        })

    # Use GPT to refine rankings and provide justifications
    system_prompt = """You are an internal mobility advisor.
Given an employee profile and candidate positions, rank the best matches and explain why.

Return valid JSON with:
- matches (list of {position_id, title, department, fit_score, justification, growth_areas})
- top_recommendation (string, brief summary of best match)
"""

    user_prompt = f"""EMPLOYEE PROFILE:
Name: {employee_profile.get('name', 'N/A')}
Current Role: {employee_profile.get('current_role', 'N/A')}
Skills: {', '.join(employee_profile.get('skills', []))}
Experience: {employee_profile.get('experience_years', 0)} years
Career Interests: {', '.join(employee_profile.get('career_interests', []))}
Preferred Locations: {', '.join(employee_profile.get('preferred_locations', []))}

CANDIDATE POSITIONS:
{json.dumps(candidate_positions, indent=2)}
"""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=Config.MAX_TOKENS,
        temperature=0.3,
        response_format={"type": "json_object"}
    )

    mobility_result = json.loads(response.choices[0].message.content)
    mobility_result["usage"] = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens
    }

    return mobility_result


def generate_workforce_plan(department_data: dict) -> dict:
    """
    Generate GenAI-powered workforce planning insights.

    Args:
        department_data: Department details including headcount, attrition, skills inventory,
                         budget, and strategic goals

    Returns:
        Workforce plan with hiring recommendations, reskilling priorities, and forecasts
    """
    client = get_openai_client()

    system_prompt = """You are a strategic workforce planning advisor.
Analyze department data and provide actionable workforce planning recommendations.

INSTRUCTIONS:
1. Assess current workforce composition and capacity
2. Identify risks such as attrition, skill concentration, and succession gaps
3. Recommend hiring priorities with role specifications
4. Propose reskilling and upskilling initiatives
5. Forecast headcount needs for the next 4 quarters
6. Align recommendations with the department's strategic goals

Return valid JSON with:
- current_assessment (string)
- risk_factors (list of {risk, severity, mitigation})
- hiring_plan (list of {role, priority, quarter, justification})
- reskilling_initiatives (list of {initiative, target_audience, expected_impact})
- quarterly_forecast (list of {quarter, projected_headcount, net_change})
- budget_implications (string)
- strategic_alignment_score (float, 0.0 to 1.0)
- executive_summary (string)
"""

    user_prompt = f"""DEPARTMENT DATA:
Department: {department_data.get('department_name', 'N/A')}
Current Headcount: {department_data.get('headcount', 0)}
Annual Attrition Rate: {department_data.get('attrition_rate', 'N/A')}%
Open Positions: {department_data.get('open_positions', 0)}
Average Tenure: {department_data.get('avg_tenure_years', 'N/A')} years
Budget (Annual): ${department_data.get('annual_budget', 'N/A')}

SKILLS INVENTORY:
{json.dumps(department_data.get('skills_inventory', {}), indent=2)}

STRATEGIC GOALS:
{json.dumps(department_data.get('strategic_goals', []), indent=2)}

RECENT ATTRITION DETAILS:
{json.dumps(department_data.get('recent_attrition', []), indent=2)}
"""

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=Config.MAX_TOKENS,
        temperature=0.4,
        response_format={"type": "json_object"}
    )

    plan_result = json.loads(response.choices[0].message.content)
    plan_result["generated_at"] = datetime.utcnow().isoformat()
    plan_result["usage"] = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens
    }

    return plan_result


# ==============================================================================
# HTTP Endpoints
# ==============================================================================

@app.route(route="screen-resume", methods=["POST"])
async def screen_resume_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Resume screening endpoint.

    Request Body:
    {
        "resume_text": "Full text of the resume...",
        "job_requirements": {
            "title": "Senior Data Engineer",
            "required_skills": ["Python", "SQL", "Spark"],
            "preferred_skills": ["Azure", "Databricks"],
            "min_experience_years": 5,
            "education": "Bachelor's in Computer Science"
        }
    }
    """
    try:
        req_body = req.get_json()
        resume_text = req_body.get("resume_text")
        job_requirements = req_body.get("job_requirements")

        if not resume_text or not job_requirements:
            return func.HttpResponse(
                json.dumps({"error": "resume_text and job_requirements are required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Screening resume for position: {job_requirements.get('title', 'Unknown')}")

        result = screen_resume(resume_text, job_requirements)

        # Persist screening result to Cosmos DB
        container = get_cosmos_container("screenings")
        screening_record = {
            "id": hashlib.md5(f"{resume_text[:100]}-{datetime.utcnow().isoformat()}".encode()).hexdigest(),
            "timestamp": datetime.utcnow().isoformat(),
            "job_title": job_requirements.get("title", "Unknown"),
            "overall_score": result.get("overall_score", 0),
            "recommendation": result.get("recommendation", "UNKNOWN"),
            "result": result
        }
        container.create_item(body=screening_record)

        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error screening resume: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="skill-gap", methods=["POST"])
async def skill_gap_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Skill gap analysis endpoint.

    Request Body:
    {
        "employee_skills": ["Python", "SQL", "Machine Learning"],
        "target_role": {
            "title": "Principal Data Scientist",
            "required_skills": ["Python", "Deep Learning", "MLOps", "Research"],
            "preferred_skills": ["Publications", "Team Leadership"],
            "level": "Principal",
            "department": "AI Research"
        }
    }
    """
    try:
        req_body = req.get_json()
        employee_skills = req_body.get("employee_skills")
        target_role = req_body.get("target_role")

        if not employee_skills or not target_role:
            return func.HttpResponse(
                json.dumps({"error": "employee_skills and target_role are required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Analyzing skill gaps for target role: {target_role.get('title', 'Unknown')}")

        result = analyze_skill_gaps(employee_skills, target_role)

        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error analyzing skill gaps: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="mobility-match", methods=["POST"])
async def mobility_match_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Internal mobility matching endpoint.

    Request Body:
    {
        "employee_profile": {
            "name": "Jane Smith",
            "current_role": "Software Engineer II",
            "skills": ["Python", "React", "AWS"],
            "experience_years": 6,
            "career_interests": ["Machine Learning", "Data Engineering"],
            "preferred_locations": ["Seattle", "Remote"]
        },
        "open_positions": []
    }
    """
    try:
        req_body = req.get_json()
        employee_profile = req_body.get("employee_profile")
        open_positions = req_body.get("open_positions", [])

        if not employee_profile:
            return func.HttpResponse(
                json.dumps({"error": "employee_profile is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Matching mobility for employee: {employee_profile.get('name', 'Unknown')}")

        result = match_internal_mobility(employee_profile, open_positions)

        # Persist mobility match to Cosmos DB
        container = get_cosmos_container("mobilityMatches")
        match_record = {
            "id": hashlib.md5(
                f"{employee_profile.get('name', '')}-{datetime.utcnow().isoformat()}".encode()
            ).hexdigest(),
            "timestamp": datetime.utcnow().isoformat(),
            "employee_name": employee_profile.get("name", "Unknown"),
            "current_role": employee_profile.get("current_role", "Unknown"),
            "top_recommendation": result.get("top_recommendation", ""),
            "result": result
        }
        container.create_item(body=match_record)

        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error matching internal mobility: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="workforce-plan", methods=["POST"])
async def workforce_plan_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Workforce planning insights endpoint.

    Request Body:
    {
        "department_data": {
            "department_name": "Engineering",
            "headcount": 150,
            "attrition_rate": 12.5,
            "open_positions": 15,
            "avg_tenure_years": 3.2,
            "annual_budget": 25000000,
            "skills_inventory": {"Python": 80, "Java": 45, "Cloud": 60},
            "strategic_goals": ["Migrate to cloud", "Build AI capabilities"],
            "recent_attrition": [{"role": "Senior SWE", "reason": "Comp", "tenure": 2.5}]
        }
    }
    """
    try:
        req_body = req.get_json()
        department_data = req_body.get("department_data")

        if not department_data:
            return func.HttpResponse(
                json.dumps({"error": "department_data is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Generating workforce plan for: {department_data.get('department_name', 'Unknown')}")

        result = generate_workforce_plan(department_data)

        # Persist workforce plan to Cosmos DB
        container = get_cosmos_container("workforcePlans")
        plan_record = {
            "id": hashlib.md5(
                f"{department_data.get('department_name', '')}-{datetime.utcnow().isoformat()}".encode()
            ).hexdigest(),
            "timestamp": datetime.utcnow().isoformat(),
            "department": department_data.get("department_name", "Unknown"),
            "headcount": department_data.get("headcount", 0),
            "result": result
        }
        container.create_item(body=plan_record)

        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error generating workforce plan: {e}", exc_info=True)
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
            "service": "hr-talent-intelligence",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }),
        mimetype="application/json"
    )


# ==============================================================================
# Event Grid Trigger for Resume Uploads
# ==============================================================================

@app.function_name(name="ResumeUploadTrigger")
@app.event_grid_trigger(arg_name="event")
async def resume_upload_trigger(event: func.EventGridEvent):
    """
    Triggered when a new resume is uploaded to blob storage.
    Initiates the resume processing and indexing pipeline.
    """
    try:
        event_data = event.get_json()
        blob_url = event_data.get("url")
        blob_name = blob_url.split("/")[-1]

        logger.info(f"New resume uploaded: {blob_name}")

        # Generate embedding for the uploaded resume content
        resume_content = event_data.get("content", "")
        if resume_content:
            embedding = generate_embedding(resume_content)

            # Store resume metadata in Cosmos DB
            container = get_cosmos_container("resumes")
            resume_record = {
                "id": hashlib.md5(f"{blob_name}-{datetime.utcnow().isoformat()}".encode()).hexdigest(),
                "blobUrl": blob_url,
                "blobName": blob_name,
                "uploadedAt": datetime.utcnow().isoformat(),
                "status": "processed",
                "embeddingGenerated": True
            }
            container.create_item(body=resume_record)

            logger.info(f"Resume processed and indexed: {blob_name}")
        else:
            logger.warning(f"Resume content empty, queuing for extraction: {blob_name}")

    except Exception as e:
        logger.error(f"Error processing resume upload event: {e}", exc_info=True)
        raise
