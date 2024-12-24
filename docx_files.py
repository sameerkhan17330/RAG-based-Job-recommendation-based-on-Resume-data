# download data from kaggle
## use unstructured library to fectch tags such as: unemployee name, skills, gender, experience, education
### store data for all the dataset in chunks in database
#### if a name is entered, fetch tags of entered name first, fetch description based on the given data, and return 5 descriptions 

import os
import re
import csv
from unstructured.documents.elements import Title, Text, NarrativeText
from unstructured.partition.docx import partition_docx

def extract_name(elements):
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
def extract_gender(full_text):
    """
    Detect gender based on explicit gender keywords.
    
    Args:
        full_text (str): Full text of the resume
    
    Returns:
        str: Detected gender or 'N/A'
    """
    # Lowercase for case-insensitive matching
    text_lower = full_text.lower()
    
    # Gender keywords to check
    gender_keywords = {
        'male': ['gender: male', 'sex: male', 'male gender', 'gender male'],
        'female': ['gender: female', 'sex: female', 'female gender', 'gender female']
    }
    
    # Check for explicit gender mentions
    for gender, keywords in gender_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                return gender
    
    return 'N/A'

def extract_resume_info(file_path):
    """
    Extract key information from a resume DOCX file.
    
    Args:
        file_path (str): Path to the DOCX resume file
    
    Returns:
        dict: Extracted resume information
    """
    # Default return dictionary
    resume_info = {
        'name': 'N/A',
        'gender': 'N/A',
        'experience': 'N/A',
        'education': 'N/A',
        'skills': 'N/A'
    }
    
    try:
        # Partition the DOCX file
        elements = partition_docx(filename=file_path)
        
        # Extract full text for comprehensive search
        full_text = " ".join([str(elem) for elem in elements])
        
        # Extract Name (using improved method)
        resume_info['name'] = extract_name(elements)
        
        # Extract Gender (using explicit keyword method)
        resume_info['gender'] = extract_gender(full_text)
        
        # Experience Extraction
        experience_keywords = [
            'experience', 'worked', 'employment', 'job', 
            'position', 'professional experience', 'work history'
        ]
        experience_sections = [
            elem for elem in elements 
            if any(keyword in str(elem).lower() for keyword in experience_keywords)
        ]
        experience_texts = [
            elem.text.strip() 
            for elem in experience_sections 
            if (isinstance(elem, (NarrativeText, Text)) and len(elem.text.strip()) > 20)
        ]
        resume_info['experience'] = '; '.join(experience_texts) if experience_texts else 'N/A'
        
        # Education Extraction
        education_keywords = [
            'education', 'degree', 'university', 'college', 
            'school', 'academic background', 'qualification'
        ]
        education_sections = [
            elem for elem in elements 
            if any(keyword in str(elem).lower() for keyword in education_keywords)
        ]
        education_texts = [
            elem.text.strip() 
            for elem in education_sections 
            if (isinstance(elem, (NarrativeText, Text)) and len(elem.text.strip()) > 20)
        ]
        resume_info['education'] = '; '.join(education_texts) if education_texts else 'N/A'
        
        # Skills Extraction
        skills_keywords = [
            'skills', 'technical skills', 'professional skills', 
            'programming languages', 'tools', 'technologies', 
            'key skills', 'core competencies'
        ]
        skills_sections = [
            elem for elem in elements 
            if any(keyword in str(elem).lower() for keyword in skills_keywords)
        ]
        skills_list = []
        for elem in skills_sections:
            # More comprehensive skill extraction
            potential_skills = re.findall(r'\b([A-Za-z+#\s]+)(?=,|\n|$)', str(elem))
            skills_list.extend([skill.strip() for skill in potential_skills if len(skill.strip()) > 2])
        
        resume_info['skills'] = '; '.join(set(skills_list)) if skills_list else 'N/A'
        
        return resume_info
    
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return resume_info

def process_resume_folder(folder_path, output_csv):
    """
    Process all DOCX files in a given folder and extract resume information.
    
    Args:
        folder_path (str): Path to the folder containing resume files
        output_csv (str): Path to the output CSV file
    
    Returns:
        list: List of extracted resume information
    """
    # Ensure the folder path exists
    if not os.path.exists(folder_path):
        print(f"Folder path {folder_path} does not exist.")
        return []
    
    # List to store all resume information
    all_resumes_info = []
    
    # Iterate through all files in the folder
    for filename in os.listdir(folder_path):
        # Check if file is a DOCX
        if filename.endswith('.docx'):
            file_path = os.path.join(folder_path, filename)
            
            # Extract information from the resume
            resume_info = extract_resume_info(file_path)
            
            # Add filename to the resume info
            resume_info['filename'] = filename
            
            # Append to list of resumes
            all_resumes_info.append(resume_info)
    
    # Write to CSV
    try:
        with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
            # Define fieldnames with filename as the last column
            fieldnames = ['name', 'gender', 'experience', 'education', 'skills', 'filename']
            
            # Create CSV writer
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Write header
            writer.writeheader()
            
            # Write data rows
            for resume in all_resumes_info:
                writer.writerow(resume)
        
        print(f"Resume data saved to {output_csv}")
    except Exception as e:
        print(f"Error writing to CSV: {e}")
    
    return all_resumes_info

# Example usage
if __name__ == "__main__":
    # Replace with the path to your resume folder and desired CSV output path
    resume_folder = "Resumes"
    output_csv_path = "resume_data_docx.csv"
    
    # Process all resumes in the folder and save to CSV
    processed_resumes = process_resume_folder(resume_folder, output_csv_path)
    