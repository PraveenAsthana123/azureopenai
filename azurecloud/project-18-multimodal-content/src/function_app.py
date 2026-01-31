"""
Multi-Modal Content Platform - Azure Functions
===============================================
Image/video/audio analysis and generation, brand content creation,
and accessibility tagging powered by Azure AI services.
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
from openai import AzureOpenAI
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
import requests

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
    VISION_ENDPOINT = os.getenv("VISION_ENDPOINT")
    SPEECH_ENDPOINT = os.getenv("SPEECH_ENDPOINT")
    COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
    KEY_VAULT_URL = os.getenv("KEY_VAULT_URL")
    STORAGE_ACCOUNT_URL = os.getenv("STORAGE_ACCOUNT_URL")

    # Model configurations
    GPT_MODEL = "gpt-4o"
    DALLE_MODEL = "dall-e-3"

    # Generation parameters
    MAX_TOKENS = 4096
    TEMPERATURE = 0.7
    IMAGE_SIZE = "1024x1024"
    IMAGE_QUALITY = "hd"


# ==============================================================================
# Service Clients (Lazy Initialization)
# ==============================================================================

_credential = None
_openai_client = None
_vision_client = None
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


def get_vision_client() -> ImageAnalysisClient:
    """Get Azure AI Vision client."""
    global _vision_client
    if _vision_client is None:
        _vision_client = ImageAnalysisClient(
            endpoint=Config.VISION_ENDPOINT,
            credential=get_credential()
        )
    return _vision_client


def get_cosmos_container(container_name: str):
    """Get Cosmos DB container client."""
    global _cosmos_client
    if _cosmos_client is None:
        _cosmos_client = CosmosClient(
            url=Config.COSMOS_ENDPOINT,
            credential=get_credential()
        )
    database = _cosmos_client.get_database_client("multimodal-content")
    return database.get_container_client(container_name)


# ==============================================================================
# Core Domain Functions
# ==============================================================================

def analyze_image(image_url: str) -> dict:
    """
    Analyze an image using Azure AI Vision for tags, captions, and objects.

    Args:
        image_url: Public URL of the image to analyze

    Returns:
        Dictionary with tags, captions, objects, and metadata
    """
    client = get_vision_client()

    result = client.analyze_from_url(
        image_url=image_url,
        visual_features=[
            VisualFeatures.CAPTION,
            VisualFeatures.DENSE_CAPTIONS,
            VisualFeatures.TAGS,
            VisualFeatures.OBJECTS,
            VisualFeatures.PEOPLE,
            VisualFeatures.READ
        ]
    )

    analysis = {
        "caption": result.caption.text if result.caption else None,
        "caption_confidence": result.caption.confidence if result.caption else None,
        "dense_captions": [
            {"text": dc.text, "confidence": dc.confidence, "bounding_box": dc.bounding_box}
            for dc in (result.dense_captions.list if result.dense_captions else [])
        ],
        "tags": [
            {"name": tag.name, "confidence": tag.confidence}
            for tag in (result.tags.list if result.tags else [])
        ],
        "objects": [
            {
                "name": obj.tags[0].name if obj.tags else "unknown",
                "confidence": obj.tags[0].confidence if obj.tags else 0,
                "bounding_box": {
                    "x": obj.bounding_box.x,
                    "y": obj.bounding_box.y,
                    "width": obj.bounding_box.width,
                    "height": obj.bounding_box.height
                }
            }
            for obj in (result.objects.list if result.objects else [])
        ],
        "people_count": len(result.people.list) if result.people else 0,
        "text_content": [
            line.text for block in (result.read.blocks if result.read else [])
            for line in block.lines
        ]
    }

    logger.info(f"Image analysis complete: {len(analysis['tags'])} tags, {len(analysis['objects'])} objects")
    return analysis


def generate_image(prompt: str, style: str = "natural") -> dict:
    """
    Generate an image using DALL-E 3.

    Args:
        prompt: Text description of the image to generate
        style: Image style - 'natural' or 'vivid'

    Returns:
        Dictionary with generated image URL and metadata
    """
    client = get_openai_client()

    response = client.images.generate(
        model=Config.DALLE_MODEL,
        prompt=prompt,
        size=Config.IMAGE_SIZE,
        quality=Config.IMAGE_QUALITY,
        style=style,
        n=1
    )

    image_data = response.data[0]

    result = {
        "image_url": image_data.url,
        "revised_prompt": image_data.revised_prompt,
        "style": style,
        "size": Config.IMAGE_SIZE,
        "quality": Config.IMAGE_QUALITY,
        "generated_at": datetime.utcnow().isoformat()
    }

    logger.info(f"Image generated successfully with style '{style}'")
    return result


def analyze_video(video_url: str) -> dict:
    """
    Analyze video by extracting key frames and generating scene descriptions.

    Uses Azure AI Vision and OpenAI GPT-4o for video understanding.

    Args:
        video_url: URL of the video to analyze

    Returns:
        Dictionary with scene descriptions, key frames, and metadata
    """
    client = get_openai_client()

    # Use GPT-4o vision capabilities for video frame analysis
    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert video analyst. Analyze the provided video content "
                    "and extract key scenes, objects, actions, and themes. Provide structured "
                    "analysis suitable for content indexing and accessibility."
                )
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Analyze this video and provide: 1) Scene-by-scene descriptions, "
                                "2) Key objects and people, 3) Overall themes, 4) Suggested tags."
                    },
                    {
                        "type": "video_url",
                        "video_url": {"url": video_url}
                    }
                ]
            }
        ],
        max_tokens=Config.MAX_TOKENS,
        temperature=0.3
    )

    analysis_text = response.choices[0].message.content

    # Parse the structured response using a follow-up call
    parse_response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {
                "role": "system",
                "content": "Convert the following video analysis into a structured JSON object."
            },
            {
                "role": "user",
                "content": f"Parse this analysis into JSON with keys: scenes (array), "
                           f"objects (array), themes (array), tags (array):\n\n{analysis_text}"
            }
        ],
        response_format={"type": "json_object"},
        max_tokens=2048
    )

    structured = json.loads(parse_response.choices[0].message.content)

    result = {
        "raw_analysis": analysis_text,
        "scenes": structured.get("scenes", []),
        "objects": structured.get("objects", []),
        "themes": structured.get("themes", []),
        "tags": structured.get("tags", []),
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens + parse_response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens + parse_response.usage.completion_tokens
        },
        "analyzed_at": datetime.utcnow().isoformat()
    }

    logger.info(f"Video analysis complete: {len(result['scenes'])} scenes, {len(result['tags'])} tags")
    return result


def generate_accessibility_tags(content_data: dict) -> dict:
    """
    Generate alt text, ARIA labels, and accessibility metadata using OpenAI.

    Args:
        content_data: Dictionary with content_type, url or description, and context

    Returns:
        Dictionary with alt_text, aria_label, long_description, wcag_notes
    """
    client = get_openai_client()

    content_type = content_data.get("content_type", "image")
    description = content_data.get("description", "")
    context = content_data.get("context", "")
    url = content_data.get("url")

    messages = [
        {
            "role": "system",
            "content": (
                "You are an accessibility expert specializing in WCAG 2.1 AA compliance. "
                "Generate appropriate accessibility metadata for digital content. "
                "Respond in JSON format with keys: alt_text (concise, under 125 chars), "
                "aria_label (brief functional label), long_description (detailed description "
                "for screen readers), wcag_tags (applicable WCAG criteria), "
                "semantic_role (appropriate ARIA role)."
            )
        },
        {
            "role": "user",
            "content": (
                f"Content type: {content_type}\n"
                f"Description: {description}\n"
                f"Context: {context}\n"
                f"URL: {url or 'N/A'}\n\n"
                "Generate comprehensive accessibility metadata for this content."
            )
        }
    ]

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=messages,
        response_format={"type": "json_object"},
        max_tokens=1024,
        temperature=0.3
    )

    accessibility = json.loads(response.choices[0].message.content)

    result = {
        "alt_text": accessibility.get("alt_text", ""),
        "aria_label": accessibility.get("aria_label", ""),
        "long_description": accessibility.get("long_description", ""),
        "wcag_tags": accessibility.get("wcag_tags", []),
        "semantic_role": accessibility.get("semantic_role", "img"),
        "content_type": content_type,
        "generated_at": datetime.utcnow().isoformat()
    }

    logger.info(f"Accessibility tags generated for {content_type}")
    return result


def create_brand_content(brief: str, brand_guidelines: dict) -> dict:
    """
    Generate brand-aligned content including text copy and image prompts.

    Args:
        brief: Creative brief describing the content needs
        brand_guidelines: Dictionary with tone, colors, style, audience, do_not_use

    Returns:
        Dictionary with copy variants, image prompts, and content plan
    """
    client = get_openai_client()

    tone = brand_guidelines.get("tone", "professional")
    colors = brand_guidelines.get("colors", [])
    style = brand_guidelines.get("style", "modern")
    audience = brand_guidelines.get("audience", "general")
    do_not_use = brand_guidelines.get("do_not_use", [])

    guidelines_text = (
        f"Brand Tone: {tone}\n"
        f"Brand Colors: {', '.join(colors) if colors else 'Not specified'}\n"
        f"Visual Style: {style}\n"
        f"Target Audience: {audience}\n"
        f"Avoid: {', '.join(do_not_use) if do_not_use else 'None specified'}"
    )

    response = client.chat.completions.create(
        model=Config.GPT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert brand content strategist and copywriter. "
                    "Create content that strictly adheres to brand guidelines. "
                    "Respond in JSON with keys: headline_variants (array of 3), "
                    "body_copy (primary text), tagline (short phrase), "
                    "image_prompts (array of 2 DALL-E prompts aligned with brand), "
                    "social_media_variants (object with twitter, linkedin, instagram), "
                    "content_notes (strategic rationale)."
                )
            },
            {
                "role": "user",
                "content": (
                    f"CREATIVE BRIEF:\n{brief}\n\n"
                    f"BRAND GUIDELINES:\n{guidelines_text}\n\n"
                    "Generate comprehensive brand-aligned content."
                )
            }
        ],
        response_format={"type": "json_object"},
        max_tokens=Config.MAX_TOKENS,
        temperature=Config.TEMPERATURE
    )

    content = json.loads(response.choices[0].message.content)

    result = {
        "headline_variants": content.get("headline_variants", []),
        "body_copy": content.get("body_copy", ""),
        "tagline": content.get("tagline", ""),
        "image_prompts": content.get("image_prompts", []),
        "social_media_variants": content.get("social_media_variants", {}),
        "content_notes": content.get("content_notes", ""),
        "brand_guidelines_applied": brand_guidelines,
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        },
        "created_at": datetime.utcnow().isoformat()
    }

    logger.info(f"Brand content created: {len(result['headline_variants'])} headlines, "
                f"{len(result['image_prompts'])} image prompts")
    return result


def transcribe_audio(audio_url: str) -> dict:
    """
    Transcribe audio using Azure Speech Services.

    Args:
        audio_url: URL of the audio file to transcribe

    Returns:
        Dictionary with transcription text, language, confidence, and segments
    """
    credential = get_credential()
    token = credential.get_token("https://cognitiveservices.azure.com/.default").token

    # Submit batch transcription request to Azure Speech Services
    transcription_url = f"{Config.SPEECH_ENDPOINT}/speechtotext/v3.1/transcriptions"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "contentUrls": [audio_url],
        "locale": "en-US",
        "displayName": f"transcription-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "properties": {
            "wordLevelTimestampsEnabled": True,
            "punctuationMode": "DictatedAndAutomatic",
            "profanityFilterMode": "Masked",
            "diarizationEnabled": True
        }
    }

    response = requests.post(transcription_url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()

    transcription_data = response.json()

    result = {
        "transcription_id": transcription_data.get("self", "").split("/")[-1],
        "status": transcription_data.get("status", "NotStarted"),
        "display_name": payload["displayName"],
        "locale": payload["locale"],
        "audio_url": audio_url,
        "submitted_at": datetime.utcnow().isoformat(),
        "properties": payload["properties"]
    }

    logger.info(f"Audio transcription submitted: {result['transcription_id']}")
    return result


# ==============================================================================
# HTTP Endpoints
# ==============================================================================

@app.route(route="analyze-image", methods=["POST"])
async def analyze_image_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Analyze an image for tags, captions, objects, and text.

    Request Body:
    {
        "image_url": "https://storage.blob.core.windows.net/images/photo.jpg"
    }
    """
    try:
        req_body = req.get_json()
        image_url = req_body.get("image_url")

        if not image_url:
            return func.HttpResponse(
                json.dumps({"error": "image_url is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Analyzing image: {image_url[:80]}...")
        analysis = analyze_image(image_url)

        # Persist analysis to Cosmos DB
        container = get_cosmos_container("media-analysis")
        record = {
            "id": hashlib.md5(image_url.encode()).hexdigest(),
            "type": "image",
            "source_url": image_url,
            "analysis": analysis,
            "analyzed_at": datetime.utcnow().isoformat()
        }
        container.upsert_item(body=record)

        return func.HttpResponse(
            json.dumps({"analysis": analysis}),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error analyzing image: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="generate-image", methods=["POST"])
async def generate_image_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Generate an image using DALL-E 3.

    Request Body:
    {
        "prompt": "A futuristic office building with green energy panels",
        "style": "natural"
    }
    """
    try:
        req_body = req.get_json()
        prompt = req_body.get("prompt")
        style = req_body.get("style", "natural")

        if not prompt:
            return func.HttpResponse(
                json.dumps({"error": "prompt is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Generating image with style '{style}': {prompt[:60]}...")
        result = generate_image(prompt, style)

        return func.HttpResponse(
            json.dumps({"result": result}),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error generating image: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="analyze-video", methods=["POST"])
async def analyze_video_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Analyze a video for scenes, objects, themes, and tags.

    Request Body:
    {
        "video_url": "https://storage.blob.core.windows.net/videos/clip.mp4"
    }
    """
    try:
        req_body = req.get_json()
        video_url = req_body.get("video_url")

        if not video_url:
            return func.HttpResponse(
                json.dumps({"error": "video_url is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Analyzing video: {video_url[:80]}...")
        analysis = analyze_video(video_url)

        # Persist analysis to Cosmos DB
        container = get_cosmos_container("media-analysis")
        record = {
            "id": hashlib.md5(video_url.encode()).hexdigest(),
            "type": "video",
            "source_url": video_url,
            "analysis": analysis,
            "analyzed_at": datetime.utcnow().isoformat()
        }
        container.upsert_item(body=record)

        return func.HttpResponse(
            json.dumps({"analysis": analysis}),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error analyzing video: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="accessibility-tag", methods=["POST"])
async def accessibility_tag_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Generate accessibility metadata for content.

    Request Body:
    {
        "content_type": "image",
        "description": "Company logo on blue background",
        "context": "Website header",
        "url": "https://example.com/logo.png"
    }
    """
    try:
        req_body = req.get_json()

        content_type = req_body.get("content_type")
        if not content_type:
            return func.HttpResponse(
                json.dumps({"error": "content_type is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Generating accessibility tags for {content_type}")
        tags = generate_accessibility_tags(req_body)

        return func.HttpResponse(
            json.dumps({"accessibility": tags}),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error generating accessibility tags: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="brand-content", methods=["POST"])
async def brand_content_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """
    Create brand-aligned content from a creative brief.

    Request Body:
    {
        "brief": "Launch campaign for new AI product targeting enterprise customers",
        "brand_guidelines": {
            "tone": "professional yet innovative",
            "colors": ["#0078D4", "#50E6FF"],
            "style": "modern minimalist",
            "audience": "enterprise IT decision-makers",
            "do_not_use": ["jargon", "hyperbole"]
        }
    }
    """
    try:
        req_body = req.get_json()
        brief = req_body.get("brief")
        brand_guidelines = req_body.get("brand_guidelines", {})

        if not brief:
            return func.HttpResponse(
                json.dumps({"error": "brief is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Creating brand content: {brief[:60]}...")
        content = create_brand_content(brief, brand_guidelines)

        # Persist to Cosmos DB
        container = get_cosmos_container("brand-content")
        record = {
            "id": hashlib.md5(f"{brief}-{datetime.utcnow().isoformat()}".encode()).hexdigest(),
            "brief": brief,
            "brand_guidelines": brand_guidelines,
            "content": content,
            "created_at": datetime.utcnow().isoformat()
        }
        container.upsert_item(body=record)

        return func.HttpResponse(
            json.dumps({"content": content}),
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Error creating brand content: {e}", exc_info=True)
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
            "service": "multi-modal-content-platform",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "capabilities": [
                "image-analysis",
                "image-generation",
                "video-analysis",
                "accessibility-tagging",
                "brand-content-creation",
                "audio-transcription"
            ]
        }),
        mimetype="application/json"
    )


# ==============================================================================
# Blob Trigger for New Media Asset Processing
# ==============================================================================

@app.function_name(name="MediaAssetProcessor")
@app.blob_trigger(
    arg_name="blob",
    path="media-assets/{name}",
    connection="STORAGE_CONNECTION"
)
async def media_asset_processor(blob: func.InputStream):
    """
    Triggered when a new media asset is uploaded to the media-assets container.
    Automatically analyzes the asset and generates accessibility metadata.
    """
    try:
        blob_name = blob.name
        blob_length = blob.length
        content_type = blob.uri.split(".")[-1].lower() if blob.uri else "unknown"

        logger.info(f"New media asset detected: {blob_name} ({blob_length} bytes, type: {content_type})")

        # Determine asset type and process accordingly
        image_extensions = {"jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff"}
        video_extensions = {"mp4", "avi", "mov", "mkv", "webm"}
        audio_extensions = {"wav", "mp3", "flac", "ogg", "m4a"}

        asset_url = f"{Config.STORAGE_ACCOUNT_URL}/media-assets/{blob_name}"
        processing_result = {}

        if content_type in image_extensions:
            logger.info(f"Processing image asset: {blob_name}")
            analysis = analyze_image(asset_url)
            accessibility = generate_accessibility_tags({
                "content_type": "image",
                "description": analysis.get("caption", ""),
                "url": asset_url
            })
            processing_result = {
                "asset_type": "image",
                "analysis": analysis,
                "accessibility": accessibility
            }

        elif content_type in video_extensions:
            logger.info(f"Processing video asset: {blob_name}")
            analysis = analyze_video(asset_url)
            accessibility = generate_accessibility_tags({
                "content_type": "video",
                "description": analysis.get("raw_analysis", "")[:500],
                "url": asset_url
            })
            processing_result = {
                "asset_type": "video",
                "analysis": analysis,
                "accessibility": accessibility
            }

        elif content_type in audio_extensions:
            logger.info(f"Processing audio asset: {blob_name}")
            transcription = transcribe_audio(asset_url)
            processing_result = {
                "asset_type": "audio",
                "transcription": transcription
            }

        else:
            logger.warning(f"Unsupported media type: {content_type} for {blob_name}")
            processing_result = {
                "asset_type": "unsupported",
                "note": f"File type '{content_type}' is not supported for automatic processing"
            }

        # Persist processing result to Cosmos DB
        container = get_cosmos_container("media-analysis")
        record = {
            "id": hashlib.md5(blob_name.encode()).hexdigest(),
            "blob_name": blob_name,
            "blob_size": blob_length,
            "content_type": content_type,
            "source_url": asset_url,
            "processing_result": processing_result,
            "processed_at": datetime.utcnow().isoformat()
        }
        container.upsert_item(body=record)

        logger.info(f"Media asset processing complete: {blob_name}")

    except Exception as e:
        logger.error(f"Error processing media asset {blob.name}: {e}", exc_info=True)
        raise
