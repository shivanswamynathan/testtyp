from typing import Dict, Any, Tuple, Optional
import io
import json
import logging
from langchain_core.language_models.base import BaseLanguageModel
from langchain_google_genai import GoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from PyPDF2 import PdfReader
from .llm_logger import LLMLogger
from .modelmanager import SimpleModelManager
from dotenv import load_dotenv
import os

load_dotenv()
llm_logger = LLMLogger()
logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """Clean and normalize extracted text"""
    return " ".join(text.split()).replace('\x00', '')

def extract_text_and_hyperlinks(pdf_file) -> Tuple[str, list]:
    """
    Extracts text and hyperlinks from a PDF file.
    Returns tuple of (text_content, hyperlinks)
    """
    reader = PdfReader(pdf_file)
    text_content = ""
    hyperlinks = []

    for page_num, page in enumerate(reader.pages):
        text_content += page.extract_text() or ""
        if "/Annots" in page:
            for annot in page["/Annots"]:
                annot_obj = annot.get_object()
                if "/A" in annot_obj and "/URI" in annot_obj["/A"]:
                    hyperlinks.append({
                        "page": page_num + 1,
                        "url": annot_obj["/A"]["/URI"]
                    })
    print(text_content)
    return text_content, hyperlinks

import json

def create_extraction_prompt(resume_text: str, hyperlinks: list) -> str:
    """Create the prompt for resume information extraction"""
    schema_template = {
        "basics": {
            "name": "string",
            "label": "string",
            "email": "string",
            "phone": "string",
            "url": "string",
            "summary": "string",
            "location": {
                "city": "string",
                "countryCode": "string"
            },
            "profiles": [
                {
                    "network": "string",
                    "username": "string",
                    "url": "string"
                }
            ]
        },
        "work": [
            {
                "name": "string",
                "position": "string",
                "location": "string",
                "startDate": "string",
                "endDate": "string",
                "highlights": ["string"]
            }
        ],
        "education": [
            {
                "institution": "string",
                "area": "string",
                "studyType": "string",
                "startDate": "string",
                "endDate": "string",
                "courses": ["string"]
            }
        ],
        "skills": [
            {
                "name": "string",
                "keywords": ["string"]
            }
        ],
        "projects": [
            {
                "name": "string",
                "description": "string",
                "startDate": "string",
                "endDate": "string"
            }
        ],
        "publications": [
            {
                "name": "string",
                "releaseDate": "string",
                "authors": ["string"],
                "doi": "string",
                "url": "string"
            }
        ],
        "awards": [
            {
                "title": "string",
                "awarder": "string"
            }
        ]
    }

    return f"""Extract and structure resume information from the provided text into JSON format.
Below is the resume content:
{resume_text}

Hyperlinks Extracted:
{json.dumps(hyperlinks, indent=2)}

Follow this exact structure:
{json.dumps(schema_template, indent=2)}


### Instructions:
- Extract ALL information present in the resume
- Extract summary from indirect mentions like "highlights", "key details", or introductory sections
- Standardize education titles: Convert Bachelor variations (BE, BS, etc.) to 'B.Tech'
- Format phone numbers to international format: '+[Country Code] [Number]'
- Extract and structure project descriptions with objectives, technologies, and outcomes
- Use 'YYYY-MM' format for dates, default to January if only year provided
- Extract technical keywords as skills
- Map scattered work experience appropriately
- Group similar skills under categories
- Preserve exact text for important details
- Break down compound information into appropriate fields
- Return only valid JSON without additional text"""

def remove_null_values(obj):
    """Replace null values with empty strings or arrays"""
    if isinstance(obj, dict):
        return {k: remove_null_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [remove_null_values(item) for item in obj]
    return "" if obj is None else obj

def get_model_name(model: BaseLanguageModel) -> str:
    """Get the standardized name for the model type"""
    model_mapping = {
        GoogleGenerativeAI: "gemini",
        ChatOpenAI: "openai",
        ChatDeepSeek: "deepseek"
    }
    return model_mapping.get(type(model), "unknown")

def extract_response_text(response: Any, model: BaseLanguageModel) -> str:
    """Extract text content from model response based on model type"""
    if isinstance(model, GoogleGenerativeAI):
        return response.text if hasattr(response, 'text') else str(response)
    elif isinstance(model, (ChatOpenAI, ChatDeepSeek)):
        return response.content if hasattr(response, 'content') else str(response)
    return str(response)

def save_input_json(json_data: Dict[str, Any], filename: str = "resume1input.json") -> None:
    """Save the input JSON to the specified file"""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        input_dir = os.path.join(base_dir, "tests", "assets", "input_json")
        os.makedirs(input_dir, exist_ok=True)
        
        input_path = os.path.join(input_dir, filename)
        with open(input_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving input JSON: {str(e)}")

async def convert_pdf_to_json_schema(
    pdf_content: bytes,
    save_input: bool = False
) -> Dict[str, Any]:
    """
    Convert PDF content to structured JSON schema.
    
    Args:
        pdf_content: Raw PDF file content in bytes
        save_input: Whether to save the extracted JSON to a file
        model: Optional Modelmanager instance.
    
    Returns:
        Dict containing the structured resume data or error message
    """
    try:
        
        instance = SimpleModelManager()
        model = instance.get_model()
        
        resume_text, hyperlinks = extract_text_and_hyperlinks(io.BytesIO(pdf_content))
        if not resume_text.strip():
            return {"error": "No text could be extracted from the PDF"}

        prompt = create_extraction_prompt(resume_text, hyperlinks)
        
        try:
            # Use the properly initialized model
            result = await model.ainvoke(prompt)
            logger.info(f"Extraction result: {result.response_metadata.get('token_usage').get('completion_tokens')}")
            
            response_text = extract_response_text(result, model)
            
            cleaned_result = response_text.replace('```json', '').replace('```', '').strip()
            
            try:
                response_json = json.loads(cleaned_result)
                cleaned_json = remove_null_values(response_json)

                if not isinstance(cleaned_json, dict) or "basics" not in cleaned_json:
                
                    error_msg = "Invalid JSON structure - missing required steps (Step1, Step2, Step3)"
                    llm_logger.log_interaction(
                        model_name=instance.current_model_type,
                        input_text=prompt,
                        output_text=cleaned_result,
                        metadata={"error": error_msg, "status": "failed"}
                    )
                    return {"error": error_msg}

                # Log success
                llm_logger.log_interaction(
                    model_name=instance.current_model_type,
                    input_text=prompt,
                    output_text=json.dumps(cleaned_json, indent=2),
                    metadata={"status": "success"}
                )

                if save_input:
                    save_input_json(cleaned_json)

                return cleaned_json

            except json.JSONDecodeError as e:
                llm_logger.log_interaction(
                    model_name=instance.current_model_type,
                    input_text=prompt,
                    output_text=cleaned_result,
                    metadata={"error": str(e), "status": "failed"}
                )
                return {"error": f"Invalid JSON response: {str(e)}"}
            
        except Exception as e:
            logger.error(f"PDF processing error: {str(e)}")
            return {"error": f"Extraction failed: {str(e)}"}
    except Exception as e:
        logger.error(f"PDF processing error: {str(e)}")
        return {"error": f"Extraction failed: {str(e)}"}