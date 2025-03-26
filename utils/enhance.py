import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
from langchain_core.language_models.base import BaseLanguageModel
from langchain_openai import ChatOpenAI, OpenAI
from langchain_google_genai import GoogleGenerativeAI
from langchain_deepseek import ChatDeepSeek
import os
import re
from .modelmanager import SimpleModelManager
logger = logging.getLogger(__name__)

TEMPLATE_PROMPTS = {
    "simple": {
        "summary_length": "Generate a concise and impactful summary of exactly 45-50 words, highlighting core skills, key strengths, and measurable impact. Avoid fluff or vague language; focus on tangible achievements.",
        "experience_length": "Each experience section MUST contain exactly 5 bullet points. DEFAULT to two-line entries (28-32 words each) that showcase skills applied and quantifiable results. Only use one-line entries (15-16 words) when content absolutely cannot be expanded. Each bullet MUST start with a strong action verb.",
        "education_length": "Education details MUST include exactly 3 bullet points. Each point MUST be 10-13 words long, highlighting major achievements, skills, or key projects. Use degree abbreviations such as 'BSc', 'MSc', 'BA', 'MA', and 'BE' for consistency.",
        "projects_length": "Each project entry MUST include exactly 5 bullet points. DEFAULT to two-line entries (28-32 words) focusing on impact, technologies used, and measurable outcomes. Only use one-line entries (15-16 words) when content absolutely cannot be expanded. Each bullet MUST start with a strong action verb.",
        "skills_format": "Organize skills into exactly 4 categorized headers, listing exactly 4 core skills per category. Use only concise terms that directly reflect key competencies. No descriptions or explanations allowed.",
        "awards_format": "Summarize each award in a single impactful sentence of exactly 20-25 words that emphasizes the achievement's significance, outcome, or recognition criteria. Each summary MUST include at least one metric or quantifiable impact."
    },
    "software_engineer": {
        "summary_length": "Generate a technical summary of exactly 55-60 words focusing on specialized programming skills, achievements, and measurable impact. MUST incorporate at least 5 ATS-relevant technical keywords for improved searchability.",
        "experience_length": "Each experience section MUST contain exactly 5 bullet points. DEFAULT to two-line entries (28-32 words) that demonstrate technical challenges solved and measurable outcomes. Only use one-line entries (15-16 words) when content absolutely cannot be expanded. Each bullet MUST start with a technical action verb.",
        "education_length": "Degree name should be in short like ME,BE. Education details MUST include exactly 3 bullet points. Each point MUST be 10-13 words long, highlighting relevant technical coursework, certifications, or achievements.Strictly Use degree abbreviations like 'BSc', 'MSc','BE','BTech' etc.",
        "projects_length": "Each project section MUST include exactly 5 bullet points. DEFAULT to two-line entries (28-32 words) focusing on technical challenges solved and quantifiable outcomes. Only use one-line entries (15-16 words) when content absolutely cannot be expanded. Each bullet MUST include at least one technical term or technology.",
        "skills_format": "List skills under exactly 5 technical categories with exactly 4 specialized skills per category. Each skill MUST be a specific technology, language, framework, or methodology relevant to software engineering.",
        "awards_format": "Summarize each award in a single impactful sentence of exactly 20-25 words highlighting technical achievements, innovation metrics, or leadership outcomes. Each summary MUST include at least one technical term or quantifiable result."
    }
}

SECTION_PROMPTS = {
    "basics": """
        Enhance the professional summary and basic information section.
        
        INSTRUCTIONS:
        - Create a powerful, concise professional summary that highlights core expertise.
        - CRITICAL: Summary MUST strictly adhere to {summary_length} - this is non-negotiable.
        - Ensure the job title/label accurately reflects skills and experience.
        - Keep all other personal information (name, contact, location) unchanged.
        
        JOB DESCRIPTION CONTEXT:
        {job_description}
        
        ORIGINAL CONTENT:
        {original_content}
        
        Return ONLY the enhanced JSON for this section. 
        Maintain the EXACT SAME structure but enhance the content.
    """,
    
    "work": """
        Enhance the work experience section.
        
        INSTRUCTIONS:
        - CRITICAL: Transform each bullet point into powerful achievement statements following these STRICT rules:
        - {experience_length}
        - DEFAULT to two-line entries (28-32 words) unless content absolutely cannot be expanded.
        - Each bullet MUST start with a strong action verb.
        - Each bullet MUST include at least one metric, percentage, or quantifiable achievement.
        - Focus on specific challenges faced, actions taken, and measurable results.
        - Keep company names, job titles, and dates unchanged.
        
        JOB DESCRIPTION CONTEXT:
        {job_description}
        
        ORIGINAL CONTENT:
        {original_content}
        
        Return ONLY the enhanced JSON for this section.
        Maintain the EXACT SAME structure but enhance the content.
    """,
    
    "education": """
        Enhance the education section.
        
        INSTRUCTIONS:
        - CRITICAL: MUST strictly follow these formatting rules: {education_length}
        - Each bullet point MUST be exactly 10-13 words.
        - Highlight relevant coursework and projects that align with target role.
        - Add academic achievements if applicable.
        - Keep institution names, degrees, and dates unchanged.
        
        JOB DESCRIPTION CONTEXT:
        {job_description}
        
        ORIGINAL CONTENT:
        {original_content}
        
        Return ONLY the enhanced JSON for this section.
        Maintain the EXACT SAME structure but enhance the content.
    """,
    
    "skills": """
        Enhance the skills section.
        
        INSTRUCTIONS:
        - CRITICAL: MUST strictly follow these formatting rules: {skills_format}
        - Prioritize skills mentioned in the job description.
        - Organize skills in order of relevance to the position.
        - Each skill MUST be a specific, concise term (1-3 words maximum).
        - Add any relevant skills that may be missing based on experience.
        
        JOB DESCRIPTION CONTEXT:
        {job_description}
        
        ORIGINAL CONTENT:
        {original_content}
        
        Return ONLY the enhanced JSON for this section.
        Maintain the EXACT SAME structure but enhance the content.
    """,
    
    "projects": """
        Enhance the projects section.
        
        INSTRUCTIONS:
        - CRITICAL: MUST strictly follow these formatting rules: {projects_length}
        - DEFAULT to two-line entries (28-32 words) unless content absolutely cannot be expanded.
        - Each bullet MUST start with a strong action verb.
        - Each bullet MUST highlight specific technologies, methodologies, or frameworks used.
        - Each bullet MUST include at least one quantifiable outcome or result.
        - Connect project outcomes to business impact where possible.
        
        JOB DESCRIPTION CONTEXT:
        {job_description}
        
        ORIGINAL CONTENT:
        {original_content}
        
        Return ONLY the enhanced JSON for this section.
        Maintain the EXACT SAME structure but enhance the content.
    """,
    
    "publications": """
        Enhance the publications section.
        
        INSTRUCTIONS:
        - Each publication description MUST be exactly 25-30 words.
        - Emphasize the relevance of the publication to the target position.
        - Highlight your specific contribution if multiple authors.
        - Use industry-specific terminology that aligns with the job.
        - Keep publication dates and formal details unchanged.
        
        JOB DESCRIPTION CONTEXT:
        {job_description}
        
        ORIGINAL CONTENT:
        {original_content}
        
        Return ONLY the enhanced JSON for this section.
        Maintain the EXACT SAME structure but enhance the content.
    """,
    
    "awards": """
        Enhance the awards section.
        
        INSTRUCTIONS:
        - CRITICAL: MUST strictly follow these formatting rules: {awards_format}
        - Each award summary MUST be exactly 20-25 words.
        - Each award summary MUST include at least one metric or quantifiable achievement.
        - Emphasize the significance and exclusivity of each award.
        - Connect awards to specific achievements or skills.
        - Keep award names, issuers, and dates unchanged.
        
        JOB DESCRIPTION CONTEXT:
        {job_description}
        
        ORIGINAL CONTENT:
        {original_content}
        
        Return ONLY the enhanced JSON for this section.
        Maintain the EXACT SAME structure but enhance the content.
    """
}

def clean_llm_response(response_text: str) -> str:
    """Clean the LLM response by extracting and formatting valid JSON content."""

    match = re.search(r'(\{.*\}|\[.*\])', response_text, re.DOTALL)
    if match:
        cleaned = match.group(0).replace('\n', '').strip()
        try:
            json_data = json.loads(cleaned)
            return json.dumps(json_data, indent=2) 
        except json.JSONDecodeError:
            return "Invalid JSON format"
    return "No valid JSON found"

def parse_json_safely(text: str) -> Dict:
    """Safely parse JSON, handling potential errors."""
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {str(e)}, text: {text[:100]}...")
        text = text.replace("'", '"')

        import re
        text = re.sub(r'([{,])\s*(\w+):', r'\1"\2":', text)
        try:
            return json.loads(text)
        except:
            return {}

def create_section_prompt(
    section_name: str, 
    section_data: Any, 
    job_description: Optional[str] = None,
    template_type: str = "simple"
) -> str:
    """Create a prompt for enhancing a specific resume section."""
    template_prompts = TEMPLATE_PROMPTS.get(template_type, TEMPLATE_PROMPTS['simple'])
    
    if section_name not in SECTION_PROMPTS:

        return f"""
            Enhance the {section_name} section.
            
            STRICT RULES:
            Maintain the EXACT SAME structure but enhance the content ensure that the input/output is same.
            INSTRUCTIONS:
            - Transform content to be more impactful and relevant to the target position.
            - Use strong, action-oriented language.
            - Add specific details and metrics where possible.
            
            JOB DESCRIPTION CONTEXT:
            {job_description or "Not provided"}
            
            ORIGINAL CONTENT:
            {json.dumps(section_data, indent=2)}
            
            Return ONLY the enhanced JSON for this section.
            
        """
    
    section_prompt = SECTION_PROMPTS[section_name].format(
        **template_prompts,
        job_description=job_description or "Not provided",
        original_content=json.dumps(section_data, indent=2)
    )
    
    return section_prompt

def extract_response_text(response: Any, model: BaseLanguageModel) -> str:
    """Extract the response text based on model type."""
    if isinstance(model, GoogleGenerativeAI):
        return response.text if hasattr(response, 'text') else str(response)
    elif isinstance(model, (ChatOpenAI, ChatDeepSeek, OpenAI)):
        return response.content if hasattr(response, 'content') else str(response)
    return str(response)

async def enhance_resume_section(
    section_name: str,
    section_data: Any,
    model: BaseLanguageModel,
    job_description: Optional[str] = None,
    template_type: str = "simple"
) -> Any:
    """Enhance a single section of the resume using the LLM."""
    try:
        
        section_prompt = create_section_prompt(
            section_name, 
            section_data, 
            job_description,
            template_type
        )

        response = await model.ainvoke(section_prompt)

        cleaned_response = clean_llm_response(response.content)
        
        enhanced_section = parse_json_safely(cleaned_response)

        if not enhanced_section:
            logger.warning(f"Failed to enhance section {section_name}, keeping original")
            return section_data
            
        return enhanced_section
    except Exception as e:
        logger.error(f"Error enhancing section {section_name}: {str(e)}")
        return section_data

async def enhance_resume_by_sections(
    json_data: Dict[str, Any],
    model: BaseLanguageModel,
    job_description: Optional[str] = None,
    template_type: str = "simple"
) -> Dict[str, Any]:
    """
    Enhance each section of the resume asynchronously and combine results.
    
    Args:
        json_data: The resume data in JSON format
        model: The LLM to use for enhancements
        job_description: Optional job description to tailor the resume
        template_type: Style template to use (simple or creative)
    
    Returns:
        Dict containing the enhanced resume data
    """
    if 'details' in json_data and isinstance(json_data['details'], dict):
        resume_data = json_data['details']
        has_details_wrapper = True
    else:
        resume_data = json_data
        has_details_wrapper = False
        
    enhancement_tasks = {}
    for section_name, section_data in resume_data.items():
        task = asyncio.create_task(
            enhance_resume_section(
                section_name, 
                section_data, 
                model, 
                job_description,
                template_type
            )
        )
        enhancement_tasks[section_name] = task
    
    enhanced_sections = {}
    for section_name, task in enhancement_tasks.items():
        enhanced_sections[section_name] = await task

    enhanced_resume = enhanced_sections
    
    if has_details_wrapper:
        result = {'details': enhanced_resume}
        if 'JD' in json_data:
            result['JD'] = json_data['JD']
        return result
    
    return enhanced_resume

async def enhance_resume_with_model(
    json_data: Dict[str, Any],
    job_description: Optional[str] = None,
    template_type: str = "simple"
) -> Dict[str, Any]:
    """
    Enhance resume data using the specified LLM model, section by section.
    
    Args:
        json_data: The resume data in JSON format
        job_description: Optional job description to tailor the resume
        modelmanager: Optional SimpleModelManager instance
        template_type: Style template to use (simple or creative)
    
    Returns:
        Dict containing the enhanced resume data
    """
    try:

        model = SimpleModelManager().get_model()
        jd = job_description
        if not jd and 'JD' in json_data:
            jd = json_data.get('JD')
            
        enhanced_json = await enhance_resume_by_sections(
            json_data, 
            model, 
            jd,
            template_type
        )
        
        logger.info("Resume enhancement completed successfully")
        return enhanced_json
        
    except Exception as e:
        logger.error(f"Resume enhancement failed: {str(e)}")
        return json_data

async def process_resume(
    json_data: Dict[str, Any],
    job_description: Optional[str] = None,
    template_type: str = "simple"
) -> Dict[str, Any]:
    """
    Process a resume by enhancing it section by section and rendering it.
    
    Args:
        json_data: The resume data in JSON format
        job_description: Optional job description to tailor the resume
        template_name: The template to use for rendering
        template_type: Style template to use (simple or creative)
        modelmanager: Optional SimpleModelManager instance
        
    Returns:
        Dict containing the enhanced resume data and rendered HTML
    """
    
    enhanced_json = await enhance_resume_with_model(
        json_data,
        job_description,
        template_type
    )
    
    
    return enhanced_json
    
    