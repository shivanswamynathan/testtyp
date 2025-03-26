import os
import uuid
import logging
import traceback
from pathlib import Path
from typing import Dict, Any, Optional

# Import the new custom rendering function
from .custom_typst import process_resume_with_custom_typst

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = os.path.join(BASE_DIR, 'utils', 'templates')
TYPST_TEMPLATES_DIR = os.path.join(BASE_DIR, 'utils', 'typst_templates')

def generate_resume_pdf(json_data: Dict[str, Any], theme_type: str = 'classic') -> str:
    """
    Generate a PDF resume from JSON data using the custom Typst template.
    
    Args:
        json_data: Enhanced JSON resume data
        theme_type: Theme type (not used in the custom implementation but kept for compatibility)
        
    Returns:
        Path to the generated PDF
    """
    try:
        if not json_data or not isinstance(json_data, dict):
            raise ValueError("Invalid JSON data provided")

        logger.info("Generating resume PDF using custom Typst template")
        
        # Create output directory
        TEMP_DIR = os.path.join(BASE_DIR, 'temp')
        OUTPUT_FOLDER = os.path.join(TEMP_DIR, 'output')
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        
        # Process the resume using the custom Typst implementation
        pdf_path = process_resume_with_custom_typst(
            json_data=json_data,
            typst_template_dir=TYPST_TEMPLATES_DIR,
            output_dir=OUTPUT_FOLDER
        )
        
        logger.info(f"Resume PDF generated successfully at: {pdf_path}")
        return pdf_path
        
    except Exception as e:
        logger.error(f"Resume generation failed: {e}")
        logger.error(traceback.format_exc())
        raise

def generate_resume_html(json_data, theme_type='classic'):
    """
    Generate HTML resume from JSON data.
    This function is maintained for backward compatibility but will raise an error
    as the custom Typst implementation does not support HTML generation.
    """
    logger.error("HTML generation is not supported with the custom Typst implementation")
    raise NotImplementedError("HTML generation is not supported with the custom Typst implementation")