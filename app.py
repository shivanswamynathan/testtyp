from flask import Flask, request, jsonify, send_file
import asyncio
import json
import io
import os
import uuid
import logging
from functools import wraps
from utils.extract import convert_pdf_to_json_schema
from utils.enhance import enhance_resume_with_model
from utils.render import generate_resume_pdf

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def async_route(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapped

@app.route('/process-resume', methods=['POST'])
@async_route
async def process_resume():
    try:
        if 'resume' not in request.files:
            return jsonify({"error": "No resume file provided"}), 400

        resume_file = request.files['resume']
        job_description = request.form.get('job_description')
        
        if resume_file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        pdf_content = resume_file.read()

        json_data = await convert_pdf_to_json_schema(pdf_content)
        
        if "error" in json_data:
            return jsonify({"error": json_data["error"]}), 500

        enhanced_json = await enhance_resume_with_model(
            json_data=json_data,
            job_description=job_description,
            template_type="software_engineer"
        )

        unique_id = str(uuid.uuid4())
        
        output_dir = os.path.join(os.path.dirname(__file__), 'temp', 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        pdf_filename = f"{unique_id}_resume.pdf"
        json_filename = f"{unique_id}.json"
        pdf_path = os.path.join(output_dir, pdf_filename)
        json_filepath = os.path.join(output_dir, json_filename)

        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(enhanced_json, f, indent=2)
        
        try:
            pdf_result = generate_resume_pdf(enhanced_json)
            logger.info(f"PDF generation result: {pdf_result}")

            if isinstance(pdf_result, str) and os.path.exists(pdf_result):
                pdf_path = pdf_result
            else:

                pdf_files = [f for f in os.listdir(output_dir) if f.endswith('.pdf')]
                if pdf_files:

                    pdf_files.sort(key=lambda x: os.path.getmtime(os.path.join(output_dir, x)), reverse=True)
                    pdf_path = os.path.join(output_dir, pdf_files[0])
            
            if os.path.exists(pdf_path):
                return send_file(
                    pdf_path,
                    mimetype='application/pdf',
                    as_attachment=True,
                    download_name=f"resume_{unique_id}.pdf"
                )
            else:
                logger.error(f"PDF file not found at path: {pdf_path}")
                return jsonify({"error": "Failed to generate PDF file"}), 500
                
        except Exception as e:
            logger.error(f"PDF generation error: {str(e)}")
            return jsonify({"error": f"PDF generation failed: {str(e)}"}), 500
        
    except Exception as e:
        logger.error(f"Error processing resume: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)