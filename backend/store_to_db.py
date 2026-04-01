import hashlib
from ollama import AsyncClient
from pydantic import BaseModel
import re


async def extract_student_metadata(CV_str):

    class StructuredContext(BaseModel):
        name: str
        location: str
        email: str
        skills: list[str]
        total_experience: float
        job_titles: list[str]

    response = await AsyncClient().chat(
        model='tinyllama:latest',
        messages=[{'role': 'user', 
                'content': f'''Extract the following from this CV:
        - applicant name
        - applicant location
        - applicant email
        - skills (list)
        - total years of experience (float number)
        - job titles
        
        For skills, I want you to create the format that I want as fast as you can. I only want the technical
        skills in short. An example of this would be : ['python', 'Git', ...] (do not blindly)
        create this but use it as an inspiration of the desired format.
        I do not want long sentences. Same goes for job titles. I want each element to be
        short and concise.

        Another important rule: everything that you will get in CVs will be in lowercase. I
        intentionally did it to make sure that the reuslts I will get are consistent 
        as I will store them in a database. So, make sure everything you return is in lowercase
        and consistent.
        
        CV:
        {CV_str}
        
        return JSON only
        '''}], format=StructuredContext.model_json_schema())

    student_metadata = StructuredContext.model_validate_json(response.message.content)

    return student_metadata



async def store_cv_in_db(student_collection, CV_str):

    # cleaning up the CV and turning into lower characteres
    clean_text_list = re.findall(r"[a-zA-Z0-9\.'@%+-]+", CV_str)
    clean_text_lower = ' '.join(clean_text_list).lower()

    # breaking up CV into chunks of size 300
    chunks_list = clean_text_lower.split(' ')
    each_chunk_size = 50
    documents_list = [' '.join(chunks_list[i:i+each_chunk_size]) for i in range(0, len(chunks_list), each_chunk_size)]

    # Extracting metadata from the total clean text
    student_metadata = await extract_student_metadata(clean_text_lower)

    # assigning a unique metadata ID for all the chunks related to each student
    student_metadata_id = hashlib.md5(f"{student_metadata.name}_{student_metadata.location}_{student_metadata.email}".encode()).hexdigest()

    # # Accessing the created collection in the main.py
    # from main import chroma_client
    # student_collection = chroma_client.get_collection(name='students_collection')

    # adding metadata and broken-up CV str in the vector database    
    student_collection.add(ids=[f"{student_metadata.name}_chunk_{i}" for i in range(len(documents_list))],
               documents=documents_list,
               metadatas=[{
                   "id": student_metadata_id,
                   "name": student_metadata.name,
                   "location": student_metadata.location,
                   "skills": student_metadata.skills,
                   "experience": student_metadata.total_experience,
                   "job titles": student_metadata.job_titles,
               } for _ in range(len(documents_list))]
    )
