import os
import pandas as pd
import numpy as np
from datasets import load_dataset
from supabase import create_client, Client
import ollama
import time
import json

# Environment Variables
SUPABASE_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9mZ2dua2VjdWNnYXZtZnp3ZHNjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNDYzMjYwMSwiZXhwIjoyMDUwMjA4NjAxfQ.JAV8Zpc68sEqOy7TfUmM5lgqWiL3jzO18T8BHFJKn94"
SUPABASE_URL = "https://ofggnkecucgavmfzwdsc.supabase.co"

# Initialize Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_API_KEY)

def is_empty_or_nan(value):
    """Check if a value is empty or NaN, handling arrays properly"""
    if isinstance(value, (np.ndarray, list)):
        return len(value) == 0
    if pd.isna(value):
        return True
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False

def compute_embeddings(text, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = ollama.embeddings(
                model="mxbai-embed-large",
                prompt=text
            )
            if "embedding" in response:
                embedding = response["embedding"]
                # Ensure embedding is a list
                if isinstance(embedding, np.ndarray):
                    embedding = embedding.tolist()
                return embedding
            else:
                raise ValueError("No embeddings found in response")
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Failed to generate embeddings after {max_retries} attempts: {str(e)}")
                return None
            print(f"Attempt {attempt + 1} failed, retrying...")
            time.sleep(1)

def clean_text(text):
    """Clean text, handling arrays properly"""
    if is_empty_or_nan(text):
        return ""
    return str(text).strip()

def process_field(value):
    """Process field values to ensure they're database-friendly"""
    if is_empty_or_nan(value):
        return None
    
    # Handle arrays and lists
    if isinstance(value, (np.ndarray, list)):
        # Convert numpy array to list if necessary
        if isinstance(value, np.ndarray):
            value = value.tolist()
        # Convert empty lists to None
        if len(value) == 0:
            return None
        return value
    
    # Handle numbers
    if isinstance(value, (int, float)):
        if pd.isna(value):
            return None
        return value
    
    # Handle strings
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned if cleaned else None
    
    return None

def create_job_text(row):
    fields = {
        "company_name": clean_text(row.get("company_name")),
        "job_position": clean_text(row.get("job_position")),
        "original_description": clean_text(row.get("original_description")),
        "relevant_skills": clean_text(row.get("relevant_skills")),
        "required_qualifications": clean_text(row.get("required_qualifications")),
        "job_responsibilities": clean_text(row.get("job_responsibilities")),
        "ideal_candidate_summary": clean_text(row.get("ideal_candidate_summary")),
        "benefits_offered": clean_text(row.get("benefits_offered")),
        "salary_range": clean_text(row.get("salary_range")),
        "job_type": clean_text(row.get("job_type")),
        "employment_type": clean_text(row.get("employment_type"))
    }
    return " ".join(x for x in fields.values() if x)

def create_resume_text(row):
    fields = {
        "name": clean_text(row.get("name")),
        "job_title": clean_text(row.get("job_title")),
        "gender": clean_text(row.get("gender")),
        "experience": clean_text(row.get("experience")),
        "education": clean_text(row.get("education")),
        "skills": clean_text(row.get("skills"))
    }
    return " ".join(x for x in fields.values() if x)

def insert_record(table_name, data):
    try:
        # Process all fields to ensure they're database-friendly
        processed_data = {}
        for key, value in data.items():
            processed_value = process_field(value)
            if processed_value is not None:  # Only include non-None values
                processed_data[key] = processed_value
        
        if not processed_data:
            print(f"No valid data to insert for record in {table_name}")
            return False
            
        response = supabase.table(table_name).insert(processed_data).execute()
        print(f"Successfully inserted record into {table_name}")
        return True
    except Exception as e:
        print(f"Error inserting data into {table_name}: {str(e)}")
        print(f"Problematic data: {data}")
        return False

def main():
    # Load datasets
    try:
        job_dataset = load_dataset("will4381/job-posting-classification")["train"]
        job_data = job_dataset.to_pandas()
        docx_data = pd.read_csv("resume_data_docx.csv")
        pdf_data = pd.read_csv("resume_data_pdf.csv")
    except Exception as e:
        print(f"Error loading datasets: {str(e)}")
        return

    # Process Jobs
    print("Processing jobs...")
    for idx, row in job_data.iterrows():
        try:
            complete_text = create_job_text(row)
            if not complete_text:
                print(f"Empty text for job record {idx}, skipping...")
                continue
                
            embedding = compute_embeddings(complete_text)
            if embedding:
                data = {
                    "original_description": row.get("original_description"),
                    "company_name": row.get("company_name"),
                    "job_position": row.get("job_position"),
                    "relevant_skills": row.get("relevant_skills"),
                    "required_qualifications": row.get("required_qualifications"),
                    "job_responsibilities": row.get("job_responsibilities"),
                    "ideal_candidate_summary": row.get("ideal_candidate_summary"),
                    "benefits_offered": row.get("benefits_offered"),
                    "salary_range": row.get("salary_range"),
                    "job_type": row.get("job_type"),
                    "employment_type": row.get("employment_type"),
                    "embeddings": embedding
                }
                insert_record("jobs", data)
        except Exception as e:
            print(f"Error processing job record {idx}: {str(e)}")
            continue

    # Process DOCX files
    print("Processing DOCX files...")
    for idx, row in docx_data.iterrows():
        try:
            complete_text = create_resume_text(row)
            if not complete_text:
                print(f"Empty text for DOCX record {idx}, skipping...")
                continue
                
            embedding = compute_embeddings(complete_text)
            if embedding:
                data = {
                    "name": row.get("name"),
                    "gender": row.get("gender"),
                    "experience": row.get("experience"),
                    "education": row.get("education"),
                    "skills": row.get("skills"),
                    "filename": row.get("filename"),
                    "embeddings": embedding
                }
                insert_record("docx_files", data)
        except Exception as e:
            print(f"Error processing DOCX record {idx}: {str(e)}")
            continue

    # Process PDF files
    print("Processing PDF files...")
    for idx, row in pdf_data.iterrows():
        try:
            complete_text = create_resume_text(row)
            if not complete_text:
                print(f"Empty text for PDF record {idx}, skipping...")
                continue
                
            embedding = compute_embeddings(complete_text)
            if embedding:
                data = {
                    "job_title": row.get("job_title"),
                    "gender": row.get("gender"),
                    "experience": row.get("experience"),
                    "education": row.get("education"),
                    "skills": row.get("skills"),
                    "filename": row.get("filename"),
                    "embeddings": embedding
                }
                insert_record("pdf_files", data)
        except Exception as e:
            print(f"Error processing PDF record {idx}: {str(e)}")
            continue

if __name__ == "__main__":
    main()