import os
from supabase import create_client
from groq import Groq
import numpy as np
from typing import List, Dict, Union
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.text import Text

# Initialize clients
SUPABASE_API_KEY = "your key"
SUPABASE_URL = "your url"
GROQ_API_KEY = "your groq key"


supabase = create_client(SUPABASE_URL, SUPABASE_API_KEY)
groq_client = Groq(api_key=GROQ_API_KEY)



def print_formatted_results(results: Dict):
    """Print formatted results using rich"""
    console = Console()  # Create console instance
    
    if "error" in results:
        console.print(Panel(
            f"[red]{results['error']}",
            title="[bold red]Error",
            border_style="red"
        ))
        return

    # Print Resume Profile
    console.print("\n=== RESUME ANALYSIS ===\n", style="bold white on blue")
    console.print(format_resume_profile(results["resume_data"]))
    
    # Print Matching Jobs
    console.print("\n=== TOP MATCHING JOBS ===\n", style="bold white on green")
    for idx, job in enumerate(results["matching_jobs"], 1):
        formatted_job = format_job_entry({
            "position": job.get("position"),
            "company": job.get("company_name"),
            "requirements": job.get("requirements"),
            "responsibilities": job.get("responsibilities"),
            "benefits": job.get("benefits"),
            "salary": job.get("salary")
        })
        console.print(f"\n[bold cyan]Match #{idx}:")
        console.print(formatted_job)
    
    # Print AI Recommendations
    console.print("\n=== AI CAREER ADVISOR RECOMMENDATIONS ===\n", style="bold white on magenta")
    console.print(Panel(
        results["ai_recommendations"],
        title="[bold magenta]Professional Recommendations",
        border_style="magenta",
        box=box.ROUNDED
    ))

# Update the format_job_entry function to fix the key names
def format_job_entry(job: Dict) -> Panel:
    """Format a single job entry into a rich Panel"""
    content = Text()
    content.append(f"🏢 Company: ", style="bold cyan")
    content.append(f"{job.get('company_name', 'Not specified')}\n\n")
    
    content.append("📋 Requirements:\n", style="bold cyan")
    requirements = job.get('required_qualifications', 'Not specified')
    content.append(f"{requirements}\n\n")
    
    content.append("💪 Responsibilities:\n", style="bold cyan")
    responsibilities = job.get('job_responsibilities', 'Not specified')
    content.append(f"{responsibilities}\n\n")
    
    content.append("💰 Benefits & Salary:\n", style="bold cyan")
    benefits = job.get('benefits_offered', 'Not specified')
    salary = job.get('salary_range', 'Not specified')
    content.append(f"Benefits: {benefits}\n")
    content.append(f"Salary Range: {salary}")
    
    return Panel(
        content,
        title=f"[bold blue]{job.get('job_position', 'Position Not Specified')}",
        border_style="green",
        box=box.ROUNDED
    )
def fetch_resume_by_filename(filename: str) -> Union[Dict, None]:
    """
    Fetch resume data from both PDF and DOCX tables based on filename
    """
    try:
        # Check PDF files
        pdf_response = supabase.table("pdf_files") \
            .select("*") \
            .eq("filename", filename) \
            .limit(1) \
            .execute()
            
        if pdf_response.data:
            return pdf_response.data[0]
            
        # Check DOCX files
        docx_response = supabase.table("docx_files") \
            .select("*") \
            .eq("filename", filename) \
            .limit(1) \
            .execute()
            
        if docx_response.data:
            return docx_response.data[0]
            
        return None
    except Exception as e:
        print(f"Error fetching resume: {str(e)}")
        return None

def calculate_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors
    """
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def find_matching_jobs(resume_data: Dict, limit: int = 5) -> List[Dict]:
    """
    Find matching jobs based on resume embeddings
    """
    try:
        # Get all jobs with their embeddings
        jobs_response = supabase.table("jobs") \
            .select("*") \
            .execute()
            
        if not jobs_response.data:
            return []

        # Calculate similarities
        similarities = []
        resume_embedding = resume_data.get("embeddings", [])
        
        for job in jobs_response.data:
            job_embedding = job.get("embeddings", [])
            if job_embedding and resume_embedding:
                similarity = calculate_similarity(resume_embedding, job_embedding)
                similarities.append((similarity, job))
        
        # Sort by similarity and get top matches
        similarities.sort(key=lambda x: x[0], reverse=True)
        return [job for _, job in similarities[:limit]]
    except Exception as e:
        print(f"Error finding matching jobs: {str(e)}")
        return []

def generate_job_recommendations(resume_data: Dict, matching_jobs: List[Dict]) -> str:
    """
    Generate AI-powered job recommendations based on resume and matching jobs
    """
    try:
        # Create context for AI
        resume_context = f"""
        Candidate Profile:
        Education: {resume_data.get('education', 'Not specified')}
        Skills: {resume_data.get('skills', 'Not specified')}
        Experience: {resume_data.get('experience', 'Not specified')}
        
        Top Matching Jobs:
        {[{
            'position': job.get('job_position'),
            'company': job.get('company_name'),
            'requirements': job.get('required_qualifications'),
            'responsibilities': job.get('job_responsibilities')
        } for job in matching_jobs]}
        """

        # Generate recommendations using Groq
        completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional career advisor. Analyze the candidate's profile and the matching jobs to provide personalized job recommendations. Focus on how the candidate's skills and experience align with each role."
                },
                {
                    "role": "user",
                    "content": resume_context
                }
            ],
            model="mixtral-8x7b-32768",
            temperature=0.7,
            max_tokens=1000
        )
        
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Error generating recommendations: {str(e)}")
        return "Unable to generate recommendations at this time."
def format_resume_profile(resume_data: Dict) -> Panel:
    """Format resume data into a rich Panel"""
    content = Text()
    content.append("📚 Education:\n", style="bold cyan")
    content.append(f"{resume_data.get('education', 'Not specified')}\n\n")
    content.append("🛠️ Skills:\n", style="bold cyan")
    content.append(f"{resume_data.get('skills', 'Not specified')}\n\n")
    content.append("💼 Experience:\n", style="bold cyan")
    content.append(f"{resume_data.get('experience', 'Not specified')}")
    
    return Panel(
        content,
        title="[bold blue]Resume Analysis",
        border_style="blue",
        box=box.ROUNDED
    )
def format_resume_profile(resume_data: Dict) -> Panel:
    """Format resume data into a rich Panel"""
    content = Text()
    content.append("📚 Education:\n", style="bold cyan")
    content.append(f"{resume_data.get('education', 'Not specified')}\n\n")
    content.append("🛠️ Skills:\n", style="bold cyan")
    content.append(f"{resume_data.get('skills', 'Not specified')}\n\n")
    content.append("💼 Experience:\n", style="bold cyan")
    content.append(f"{resume_data.get('experience', 'Not specified')}")
    
    return Panel(
        content,
        title="[bold blue]Resume Analysis",
        border_style="blue",
        box=box.ROUNDED
    )

def format_job_match(job: Dict, match_score: float) -> Panel:
    """Format a job match into a rich Panel with detailed company information"""
    content = Text()
    
    # Company Information
    content.append("🏢 Company Information\n", style="bold magenta")
    content.append(f"Company: {job.get('company_name', 'Not specified')}\n")
    content.append(f"Location: {job.get('location', 'Not specified')}\n")
    content.append(f"Industry: {job.get('industry', 'Not specified')}\n\n")
    
    # Position Details
    content.append("📋 Position Details\n", style="bold cyan")
    content.append(f"Role: {job.get('job_position', 'Not specified')}\n")
    content.append(f"Employment Type: {job.get('employment_type', 'Not specified')}\n")
    
    # Only show salary if it exists
    salary = job.get('salary_range')
    if salary:
        content.append(f"Salary Range: {salary}\n")
    
    # Requirements if available
    requirements = job.get('required_qualifications')
    if requirements:
        content.append("\n📋 Key Requirements:\n", style="bold yellow")
        content.append(f"{requirements}\n")
    
    # Match Score
    content.append(f"\n✨ Match Score: {match_score:.1%}\n", style="bold green")
    
    return Panel(
        content,
        title=f"[bold blue]{job.get('job_position', 'Position Not Specified')}",
        border_style="green",
        box=box.ROUNDED
    )

def deduplicate_jobs(jobs: List[tuple[Dict, float]]) -> List[tuple[Dict, float]]:
    """Remove duplicate jobs based on company and position"""
    seen = set()
    unique_jobs = []
    
    for job, score in jobs:
        # Create a unique identifier for each job using company and position
        job_key = (job.get('company_name'), job.get('job_position'))
        
        if job_key not in seen:
            seen.add(job_key)
            unique_jobs.append((job, score))
    
    return unique_jobs

def find_matching_jobs(resume_data: Dict, limit: int = 5) -> List[tuple[Dict, float]]:
    """Find matching jobs based on resume embeddings and return with match scores"""
    try:
        jobs_response = supabase.table("jobs") \
            .select("*") \
            .execute()
            
        if not jobs_response.data:
            return []

        matches = []
        resume_embedding = resume_data.get("embeddings", [])
        
        for job in jobs_response.data:
            job_embedding = job.get("embeddings", [])
            if job_embedding and resume_embedding:
                similarity = calculate_similarity(resume_embedding, job_embedding)
                matches.append((job, similarity))
        
        # Sort by similarity
        matches.sort(key=lambda x: x[1], reverse=True)
        
        # Remove duplicates
        unique_matches = deduplicate_jobs(matches)
        
        # Return top N unique matches
        return unique_matches[:limit]
    except Exception as e:
        print(f"Error finding matching jobs: {str(e)}")
        return []

def print_job_matches(resume_data: Dict, matching_jobs: List[tuple[Dict, float]]):
    """Print formatted job matches with company details"""
    console = Console()
    
    # Print Resume Profile
    console.print("\n=== RESUME ANALYSIS ===\n", style="bold white on blue")
    console.print(format_resume_profile(resume_data))
    
    # Print Matching Jobs
    console.print("\n=== TOP MATCHING COMPANIES ===\n", style="bold white on green")
    
    if not matching_jobs:
        console.print("[red]No matching jobs found.[/red]")
        return
    
    for job, match_score in matching_jobs:
        console.print(format_job_match(job, match_score))
        console.print("")  # Add spacing between jobs

def get_job_recommendations(filename: str):
    """Main function to get job recommendations based on resume filename"""
    try:
        # Fetch resume data
        resume_data = fetch_resume_by_filename(filename)
        if not resume_data:
            console = Console()
            console.print("[red]Resume not found[/red]")
            return
            
        # Find matching jobs with scores and deduplication
        matching_jobs = find_matching_jobs(resume_data)
        if not matching_jobs:
            console = Console()
            console.print("[red]No matching jobs found[/red]")
            return
            
        # Print formatted results
        print_job_matches(resume_data, matching_jobs)
        
    except Exception as e:
        console = Console()
        console.print(f"[red]Error processing request: {str(e)}[/red]")





# Example usage
if __name__ == "__main__":
    results = get_job_recommendations("Adelina_Erimia_PMP1.docx")
    print(results)