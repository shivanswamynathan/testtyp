import yaml
import os
import json
import logging
import uuid
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class EnhancedJSONToConfigConverter:
    """
    Converts enhanced JSON resume schema to the configuration.yaml format
    required by the custom Typst template.
    """
    
    def __init__(self, json_data: Dict[str, Any]):
        self.json_data = json_data
        self.config_data = {
            "contacts": {},
            "jobs": [],
            "education": [],
            "skills": [],
            "technical_expertise": [],
            "methodology": [],
            "tools": [],
            "achievements": []
        }
    
    def convert_contacts(self) -> None:
        """Convert basic information to contacts section"""
        basics = self.json_data.get("basics", {})
        
        self.config_data["contacts"]["name"] = basics.get("name", "")
        self.config_data["contacts"]["title"] = basics.get("label", "")
        self.config_data["contacts"]["email"] = basics.get("email", "")
        
        # Handle location
        location = basics.get("location", {})
        if isinstance(location, dict):
            city = location.get("city", "")
            country = location.get("countryCode", "")
            self.config_data["contacts"]["address"] = f"{city}, {country}" if city and country else city or country
            self.config_data["contacts"]["location"] = country or city
        
        # Set position from label
        self.config_data["position"] = basics.get("label", "")
        
        # Handle profiles (LinkedIn, GitHub, etc.)
        profiles = basics.get("profiles", [])
        for profile in profiles:
            if not isinstance(profile, dict):
                continue
                
            network = profile.get("network", "").lower()
            if network == "linkedin":
                self.config_data["contacts"]["linkedin"] = {
                    "url": profile.get("url", ""),
                    "displayText": profile.get("username", "")
                }
            elif network == "github":
                self.config_data["contacts"]["github"] = {
                    "url": profile.get("url", ""),
                    "displayText": f"@{profile.get('username', '')}"
                }
        
        # Handle website
        if basics.get("url"):
            self.config_data["contacts"]["website"] = {
                "url": basics.get("url", ""),
                "displayText": basics.get("url", "").replace("https://", "").replace("http://", "")
            }
        
        # Set tagline from summary
        self.config_data["tagline"] = basics.get("summary", "")
    
    def convert_work_experience(self) -> None:
        """Convert work experience to jobs section"""
        work_entries = self.json_data.get("work", [])
        
        for entry in work_entries:
            if not isinstance(entry, dict):
                continue
                
            job = {
                "position": entry.get("position", ""),
                "company": {
                    "name": entry.get("name", ""),
                    "link": f"https://{entry.get('name', '').lower().replace(' ', '')}.com/"
                },
                "product": {
                    "name": entry.get("name", ""),
                    "link": f"https://{entry.get('name', '').lower().replace(' ', '')}.com"
                },
                "description": entry.get("highlights", []),
                "from": self._format_date(entry.get("startDate", "")),
                "to": self._format_date(entry.get("endDate", "")),
                "location": entry.get("location", ""),
                "tags": self._extract_tags_from_highlights(entry.get("highlights", []))
            }
            
            self.config_data["jobs"].append(job)
    
    def convert_education(self) -> None:
        """Convert education entries"""
        education_entries = self.json_data.get("education", [])
        
        # Handle different education formats
        if isinstance(education_entries, dict) and "education" in education_entries:
            education_entries = education_entries.get("education", [])
        
        for entry in education_entries:
            if not isinstance(entry, dict):
                continue
                
            institution = entry.get("institution", "")
            degree = entry.get("degree", "") or entry.get("studyType", "")
            major = entry.get("area", "")
            
            edu = {
                "place": {
                    "name": institution,
                    "link": f"http://{institution.lower().replace(' ', '')}.edu" if institution else ""
                },
                "degree": degree,
                "major": major,
                "track": major,
                "from": self._extract_year_from_date(entry.get("startDate", "") or entry.get("date", "")),
                "to": self._extract_year_from_date(entry.get("endDate", "") or entry.get("date", "")),
                "location": entry.get("location", "")
            }
            
            self.config_data["education"].append(edu)
    
    def convert_skills(self) -> None:
        """Convert skills section"""
        skills_entries = self.json_data.get("skills", [])
        
        all_skills = []
        methodology = []
        tools = []
        technical_expertise = []
        
        for skill_group in skills_entries:
            if not isinstance(skill_group, dict):
                continue
                
            category = skill_group.get("name", "").lower()
            keywords = skill_group.get("keywords", [])
            
            if not keywords:
                continue
                
            if "method" in category or "approach" in category:
                methodology.extend(keywords)
            elif "tool" in category or "environment" in category:
                tools.extend(keywords)
            elif "technical" in category or "language" in category or "framework" in category:
                # Add to technical expertise with random level between 3-5
                import random
                for tech in keywords:
                    technical_expertise.append({
                        "name": tech,
                        "level": random.randint(3, 5)
                    })
            else:
                all_skills.extend(keywords)
        
        self.config_data["skills"] = all_skills
        self.config_data["methodology"] = methodology
        self.config_data["tools"] = tools
        self.config_data["technical_expertise"] = technical_expertise or [
            {"name": "Skill 1", "level": 4},
            {"name": "Skill 2", "level": 5}
        ]
    
    def convert_projects_to_achievements(self) -> None:
        """Convert projects to achievements section"""
        projects = self.json_data.get("projects", [])
        
        for project in projects:
            if not isinstance(project, dict):
                continue
                
            name = project.get("name", "")
            
            # Get description from either a string or the first item in a list
            description = project.get("description", "")
            if isinstance(description, list) and description:
                description = description[0]
                
            achievement = {
                "name": name,
                "description": description
            }
            
            self.config_data["achievements"].append(achievement)
    
    def convert_certifications(self) -> None:
        """Convert certifications to achievements section"""
        certifications = self.json_data.get("certifications", [])
        
        for cert in certifications:
            if not isinstance(cert, dict):
                continue
                
            name = cert.get("title", "")
            description = cert.get("description", "") or f"Issued by {cert.get('awarder', '')}"
            
            achievement = {
                "name": name,
                "description": description
            }
            
            self.config_data["achievements"].append(achievement)
    
    def add_objective(self) -> None:
        """Add a default objective if none exists"""
        self.config_data["objective"] = "Seeking to leverage my skills and experience to contribute to innovative projects and advance my career in a dynamic environment."
    
    def _format_date(self, date_str: str) -> str:
        """Format date string to the required format: 'YYYY Mon.' or 'present'"""
        if not date_str:
            return ""
            
        if date_str.lower() == "present":
            return "present"
            
        try:
            # Try parsing YYYY-MM format
            if "-" in date_str:
                year, month = date_str.split("-")
                month_int = int(month)
                month_abbr = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][month_int - 1]
                return f"{year} {month_abbr}."
            else:
                # Just a year
                return date_str
        except Exception:
            return date_str
    
    def _extract_year_from_date(self, date_str: str) -> str:
        """Extract the year from a date string"""
        if not date_str:
            return ""
            
        if date_str.lower() == "present":
            return "present"
            
        try:
            # Try to extract year from various formats
            if "-" in date_str:
                return date_str.split("-")[0]
            
            # Extract 4-digit year using regex
            import re
            year_match = re.search(r'\b(19|20)\d{2}\b', date_str)
            if year_match:
                return year_match.group(0)
                
            return date_str
        except Exception:
            return date_str
    
    def _extract_tags_from_highlights(self, highlights: List[str]) -> List[str]:
        """Extract potential tags from work highlights"""
        if not highlights:
            return []
            
        # Extract technical terms that could be tags
        all_text = " ".join(highlights)
        import re
        
        # Look for capitalized terms or terms in quotes
        potential_tags = re.findall(r'\b([A-Z][a-zA-Z]+)\b|\b([A-Z][A-Z]+)\b|"([^"]+)"', all_text)
        
        # Flatten the list of tuples and remove empty strings
        tags = [t for tup in potential_tags for t in tup if t]
        
        # Only keep unique values and limit to 3
        unique_tags = list(set(tags))[:3]
        
        # If we couldn't extract tags, create some generic ones
        if not unique_tags and len(highlights) > 0:
            words = highlights[0].split()
            if len(words) >= 3:
                unique_tags = [words[0], words[2], "Development"]
            else:
                unique_tags = ["Development", "Implementation", "Design"]
        
        return unique_tags
    
    def convert(self) -> Dict[str, Any]:
        """Convert the JSON resume to configuration.yaml format"""
        self.convert_contacts()
        self.convert_work_experience()
        self.convert_education()
        self.convert_skills()
        self.convert_projects_to_achievements()
        self.convert_certifications()
        self.add_objective()
        
        return self.config_data

def save_yaml_config(data: Dict[str, Any], output_path: str) -> None:
    """Save the configuration data as YAML"""
    try:
        with open(output_path, 'w', encoding='utf-8') as file:
            yaml.dump(data, file, default_flow_style=False, sort_keys=False, allow_unicode=True)
        logger.info(f"Configuration YAML saved to {output_path}")
    except Exception as e:
        logger.error(f"Error saving YAML configuration: {str(e)}")
        raise

def prepare_typst_environment(template_dir: str, output_dir: str) -> str:
    """
    Prepares a working directory for Typst by copying necessary files
    
    Args:
        template_dir: Source directory with Typst templates
        output_dir: Target directory for processing
        
    Returns:
        Path to the working directory
    """
    import shutil
    
    # Create a unique working directory
    work_dir = os.path.join(output_dir, f"typst_work_{uuid.uuid4()}")
    os.makedirs(work_dir, exist_ok=True)
    
    # Copy all template files to working directory
    source_files = [
        "example.typ",
        "vantage-typst.typ",
    ]
    
    for file_name in source_files:
        src = os.path.join(template_dir, file_name)
        dst = os.path.join(work_dir, file_name)
        try:
            shutil.copy2(src, dst)
            logger.info(f"Copied {file_name} to {work_dir}")
        except FileNotFoundError:
            logger.error(f"Template file not found: {src}")
            raise FileNotFoundError(f"Template file not found: {src}")
    
    # Create icons directory
    icons_dir = os.path.join(work_dir, "icons")
    os.makedirs(icons_dir, exist_ok=True)
    
    # Create minimalist SVG icons for the required icons
    icons = {
        "calendar": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>',
        "location": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>',
        "email": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><polyline points="22,6 12,13 2,6"></polyline></svg>',
        "website": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>',
        "github": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"></path></svg>',
        "linkedin": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"></path><rect x="2" y="9" width="4" height="12"></rect><circle cx="4" cy="4" r="2"></circle></svg>'
    }
    
    # Save the icons
    for icon_name, svg_content in icons.items():
        icon_path = os.path.join(icons_dir, f"{icon_name}.svg")
        with open(icon_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        logger.info(f"Created icon: {icon_path}")
    
    return work_dir

def generate_pdf_from_typst(yaml_path: str, typst_template_dir: str, output_dir: str) -> str:
    """
    Generate a PDF from the Typst template and the configuration YAML
    
    Args:
        yaml_path: Path to the configuration.yaml file
        typst_template_dir: Directory containing Typst templates
        output_dir: Directory to save the generated PDF
        
    Returns:
        Path to the generated PDF
    """
    try:
        # Create a unique output filename
        output_filename = f"{uuid.uuid4()}_resume.pdf"
        output_path = os.path.join(output_dir, output_filename)
        
        # Prepare working directory with all necessary files
        work_dir = prepare_typst_environment(typst_template_dir, output_dir)
        
        # Copy configuration.yaml to working directory
        work_yaml_path = os.path.join(work_dir, "configuration.yaml")
        import shutil
        shutil.copy2(yaml_path, work_yaml_path)
        
        # Path to example.typ in the working directory
        typst_template_path = os.path.join(work_dir, "example.typ")
        
        # Check if Typst is installed
        try:
            version_cmd = ["typst", "--version"]
            subprocess.run(version_cmd, check=True, capture_output=True, text=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("Typst is not installed or not in PATH")
            raise RuntimeError("Typst is not installed or not in PATH. Please install Typst: https://github.com/typst/typst")
        
        # Compile the Typst template to PDF
        cmd = ["typst", "compile", typst_template_path, output_path]
        logger.info(f"Running command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            cwd=work_dir,  # Run in the working directory
            check=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Error compiling Typst template: {result.stderr}")
            raise RuntimeError(f"Typst compilation failed: {result.stderr}")
        
        logger.info(f"PDF generated successfully at {output_path}")
        
        # Clean up working directory
        try:
            shutil.rmtree(work_dir)
        except Exception as e:
            logger.warning(f"Failed to clean up working directory: {str(e)}")
        
        return output_path
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Error calling Typst: {e.stderr}")
        raise RuntimeError(f"Typst compilation failed: {e.stderr}")
    except Exception as e:
        logger.error(f"Error generating PDF from Typst: {str(e)}")
        raise

def process_resume_with_custom_typst(
    json_data: Dict[str, Any],
    typst_template_dir: str,
    output_dir: str
) -> str:
    """
    Process a resume by converting the JSON data to the configuration.yaml format
    and generating a PDF using the custom Typst template.
    
    Args:
        json_data: Enhanced JSON resume data
        typst_template_dir: Directory containing the Typst templates
        output_dir: Directory to save the generated files
        
    Returns:
        Path to the generated PDF
    """
    try:
        # Convert JSON to configuration.yaml format
        converter = EnhancedJSONToConfigConverter(json_data)
        config_data = converter.convert()
        
        # Create file paths
        os.makedirs(output_dir, exist_ok=True)
        yaml_filename = f"{uuid.uuid4()}_configuration.yaml"
        yaml_path = os.path.join(output_dir, yaml_filename)
        
        # Save the configuration.yaml
        save_yaml_config(config_data, yaml_path)
        
        # Generate PDF using Typst
        pdf_path = generate_pdf_from_typst(yaml_path, typst_template_dir, output_dir)
        
        # Clean up the temporary YAML file
        try:
            os.remove(yaml_path)
            logger.info(f"Removed temporary YAML file: {yaml_path}")
        except Exception as e:
            logger.warning(f"Failed to remove temporary YAML file: {str(e)}")
        
        return pdf_path
    except Exception as e:
        logger.error(f"Error processing resume with custom Typst: {str(e)}")
        raise