from pydantic import BaseModel
import numpy as np
from ollama import chat
from collections import defaultdict


multiplier = 15

def weighted_score(skills_score, experience_score, mean_semantic_dist, weights=None):
    weights = weights or {
        'skills_weight': 0.3,
        'experience_weight': 0.2,
        'semantic_weight': 0.5
    }

    skills_score = skills_score * weights['skills_weight']
    experience_score = experience_score * weights['experience_weight']
    semantic_score = 1 / (1 + mean_semantic_dist)
    semantic_score  = semantic_score * weights['semantic_weight']

    return (skills_score + experience_score + semantic_score)


def extract_job_desc_metadata(jd: str):
    class JDStructuredContext(BaseModel):
        compnay_name: str
        job_title: str
        location: str
        skills_required: list[str]
        required_experience: float

    
    response = chat(
        model='tinyllama:latest',
        messages=[{'role': 'user', 
                'content': f'''Extract the following from this CV:
        - company name
        - company location
        - skills required (list)
        - total years of required experience (float number)
        - job title
        
        For required skills, I want you to create the format that I want. I only want 
        the technical skills in short. An example of this 
        would be : ['python', 'Git', ...] (do not blindly
        create this but use it as an inspiration for the desired format).
        I do not want long sentences. Same goes for job titles. I want each element to be
        short and concise.

        Another important rule: everything that you will get in the job description will be in 
        lowercase. I intentionally did it to make sure that the reuslts I 
        will get are consistent as I will store them in a database. So, 
        make sure everything you return is in lowercase and consistent.
        
        Job Description:
        {jd}
        
        return JSON only
        '''}], format=JDStructuredContext.model_json_schema())

    jd_metadata = JDStructuredContext.model_validate_json(response.message.content)
    return jd_metadata



def get_top_applicants(student_collection, jd: str, n_top_applicants=5):
 

    if student_collection.count() < 1:
        return {
            'status': 'failed',
            'result': []
        }

    # extract job description's metadata
    jd_metadata = extract_job_desc_metadata(jd)

    # limiting the number of results to avoid errors
    limit_results = min(student_collection.count(), n_top_applicants * multiplier)

    # querying job description which the collection we have to get the similarity 
    # for each
    result = student_collection.query(
        query_texts=jd,
        n_results=limit_results
    )

    added_applicant = 0

    # defining unique applicants as defaultdict in order to store 
    # values that will be needed moving forward
    unique_applicants = defaultdict(lambda: {
        "dist": [],
        "meta": None,
        'final_score': 0.0
    })

    # loop throught the top chunks and store multiple distances for the same candidate 
    # when needed. The computation of score will be done in the next stage
    for each_chunk in range(limit_results):
        candidate_metadata_id = result['metadatas'][0][each_chunk]['id']
        candidate_distance = result["distances"][0][each_chunk]
        candidate_meta = result['metadatas'][0][each_chunk]

        # if candidate_metadata_id not in unique_applicants.keys():
        #     added_applicant += 1
        #     if added_applicant > n_top_applicants + 1:
        #         break

        unique_applicants[candidate_metadata_id]["dist"].append(candidate_distance)
        if unique_applicants[candidate_metadata_id]["meta"] is None:
            unique_applicants[candidate_metadata_id]["meta"] = candidate_meta



    # compute the hybrid compatibility score for each top candidate
    for candidate_id, candidate_data in unique_applicants.items():
        
        skills_score = (
            len(set(candidate_data['meta']['skills']) & set(jd_metadata.skills_required)) 
            / len(jd_metadata.skills_required)
            if jd_metadata.skills_required else 0
        )

        experience_score = (
            min(candidate_data['meta']['experience'] / jd_metadata.required_experience, 1.0)
            if jd_metadata.required_experience else 0
        )

        mean_semantic_dist = np.mean(candidate_data['dist'])

        average_score = weighted_score(
            skills_score=skills_score,
            experience_score=experience_score,
            mean_semantic_dist=mean_semantic_dist,
            weights=None
        )
        
        unique_applicants[candidate_id]['final_score'] = average_score.item()


    # now it's time to sort top candidates based on their final scores
    # which is a combination of their semantic score, skills, and 
    # experience compatibility
    ranked_applicants = sorted(unique_applicants.values(), key=lambda applicant: applicant['final_score'], reverse=True)


    # return top required applicants info in a list of dictionaries
    top_applicants_info = []
    for rank, applicant in enumerate(ranked_applicants[:n_top_applicants], 1):
        print(rank, applicant['meta']['name'], applicant['meta']['location'], f"{round(applicant['final_score'] * 100, 2)}%")
        
        top_applicants_info.append({
            'rank': rank,
            'name': applicant['meta']['name'],
            'location': applicant['meta']['location'],
            'experience': f"{round(applicant['meta']['experience'], 2)}",
            'compatibility': f"{round(applicant['final_score'] * 100, 2)}%"
        })

    return {
        'status': 'success',
        'result': top_applicants_info
    }

    
