import os
import re
import csv
from unstructured.documents.elements import Title, Text, NarrativeText, ListItem
from unstructured.partition.auto import partition

def extract_job_title(elements):
     # Check for Title elements (likely candidate for names)
    name_candidates = [elem.text.strip() for elem in elements if isinstance(elem, Title)]
    if name_candidates:
        return name_candidates[0]
    
    # Fallback: Check the first few text elements for names
    text_candidates = [elem.text.strip() for elem in elements if isinstance(elem, Text)][:3]
    for text in text_candidates:
        # Use a regex to find probable name patterns (e.g., Capitalized First Last)
        match = re.search(r'^[A-Z][a-z]+(?:\s[A-Z][a-z]+)+$', text)
        if match:
            return match.group(0)
    
    return 'N/A'

def extract_experience(elements):
    """
    Enhanced experience extraction with debugging.
    """
    experience_texts = []
    in_experience_section = False
    experience_keywords = [
        'experience', 'employment history', 'work history', 
        'professional background', 'career history'
    ]
    
    for elem in elements:
        elem_text = str(elem).lower().strip()
        
        # Debug section detection
        if any(keyword in elem_text for keyword in experience_keywords) and isinstance(elem, (Title, Text)):
            in_experience_section = True
            continue
            
        if in_experience_section and isinstance(elem, Title) and \
           any(keyword in elem_text for keyword in ['education', 'skills', 'certifications']):
            in_experience_section = False
            
        if in_experience_section and isinstance(elem, (NarrativeText, ListItem)):
            text = elem.text.strip()
            if len(text) > 20 and not any(keyword in text.lower() for keyword in experience_keywords):
                experience_texts.append(text)
    
    result = '; '.join(experience_texts) if experience_texts else 'N/A'
    return result

def extract_education(elements):
    """
    Enhanced education extraction with debugging.
    """
    education_texts = []
    in_education_section = False
    education_keywords = [
        'education', 'academic', 'degree', 'university', 
        'college', 'school', 'qualification'
    ]
    
    for elem in elements:
        elem_text = str(elem).lower().strip()
        
        if any(keyword in elem_text for keyword in education_keywords) and isinstance(elem, (Title, Text)):
            in_education_section = True
            continue
            
        if in_education_section and isinstance(elem, Title) and \
           any(keyword in elem_text for keyword in ['experience', 'skills', 'certifications']):
            in_education_section = False
            
        if in_education_section and isinstance(elem, (NarrativeText, ListItem, Text)):
            text = elem.text.strip()
            if len(text) > 20 and not any(keyword in text.lower() for keyword in education_keywords):
                education_texts.append(text)
    
    result = '; '.join(education_texts) if education_texts else 'N/A'
    return result

def extract_skills(elements):
    """
    Enhanced skills extraction with debugging.
    """
    skills_texts = []
    in_skills_section = False
    skills_keywords = [
        'skills', 'technical skills', 'competencies', 
        'expertise', 'technologies', 'tools'
    ]
    
    for elem in elements:
        elem_text = str(elem).lower().strip()
        
        if any(keyword in elem_text for keyword in skills_keywords) and isinstance(elem, (Title, Text)):
            in_skills_section = True
            continue
            
        if in_skills_section and isinstance(elem, Title) and \
           any(keyword in elem_text for keyword in ['experience', 'education', 'references']):
            in_skills_section = False
            
        if in_skills_section and isinstance(elem, (NarrativeText, ListItem, Text)):
            text = elem.text.strip()
            skills = re.findall(r'[\w\+\#\-\.\s]{2,25}(?:,|\n|$)', text)
            skills = [skill.strip() for skill in skills if len(skill.strip()) > 2]
            if skills:
                skills_texts.extend(skills)
    
    result = '; '.join(set(skills_texts)) if skills_texts else 'N/A'
    return result

def extract_resume_info(file_path):
    """
    Extract key information from a PDF resume file with enhanced debugging.
    """
    resume_info = {
        'job_title': 'N/A',
        'gender': 'N/A',
        'experience': 'N/A',
        'education': 'N/A',
        'skills': 'N/A'
    }
    
    try:
        elements = partition(filename=file_path)

        # Extract details
        resume_info['job_title'] = extract_job_title(elements)
        resume_info['experience'] = extract_experience(elements)
        resume_info['education'] = extract_education(elements)
        resume_info['skills'] = extract_skills(elements)

        # Gender extraction
        full_text = " ".join([str(elem) for elem in elements]).lower()
        gender_keywords = {
            'male': ['gender: male', 'sex: male', 'male gender', 'gender male'],
            'female': ['gender: female', 'sex: female', 'female gender', 'gender female']
        }
        for gender, keywords in gender_keywords.items():
            if any(keyword in full_text for keyword in keywords):
                resume_info['gender'] = gender
                break

        return resume_info
    
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        import traceback
        traceback.print_exc()
        return resume_info

def process_resume_folder(folder_path, output_csv):
    """
    Recursively process all PDF files in a given folder (and its subfolders)
    and extract resume information.
    """
    if not os.path.exists(folder_path):
        print(f"Folder path does not exist: {folder_path}")
        return []
    
    all_resumes_info = []
    
    # Traverse folder and subfolders
    for root, _, files in os.walk(folder_path):
        for filename in files:
            if filename.endswith('.pdf'):  # Only process PDF files
                file_path = os.path.join(root, filename)
                
                try:
                    resume_info = extract_resume_info(file_path)
                    resume_info['filename'] = os.path.relpath(file_path, folder_path)  # Use relative path for clarity
                    all_resumes_info.append(resume_info)
                    print(f"✓ Successfully processed: {file_path}")
                except Exception as e:
                    print(f"❌ Error processing {file_path}: {str(e)}")
                    import traceback
                    traceback.print_exc()
    
    # Write all extracted resume information to a CSV file
    try:
        with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['filename', 'job_title', 'gender', 'experience', 'education', 'skills']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for resume in all_resumes_info:
                writer.writerow(resume)
        
        print(f"\nProcessing complete! Resume data saved to {output_csv}")
        print(f"Total resumes processed: {len(all_resumes_info)}")
    except Exception as e:
        print(f"Error writing to CSV: {e}")
        import traceback
        traceback.print_exc()
    
    return all_resumes_info

if __name__ == "__main__":
    resume_folder = "data"  # Replace with your PDF folder path
    output_csv_path = "resume_data_pdf.csv"
    
    processed_resumes = process_resume_folder(resume_folder, output_csv_path)