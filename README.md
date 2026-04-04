# Job CV Matcher


A full-stack Python system with a FastAPI backend, Streamlit frontend, 
and a multi-container Docker setup that automates candidate screening 
using local LLM inference and vector search. No cloud APIs required.

---

## What it does

HR screening is slow. Job CV Matcher automates it.

Upload any number of CVs (PDF or DOCX) and they get parsed, cleaned, chunked, and stored in a vector database — each candidate represented by their actual content, not just keywords. When you upload a job description, the system queries that database and ranks candidates using a **hybrid score** built from three signals: how semantically similar their CV is to the role, how much their skills overlap with what's required, and whether their experience meets the bar.

The result is a clean ranked table with a compatibility percentage for each candidate — colour-coded green, amber, or red.

---

## Under the hood

**Ingestion** — each CV is cleaned and lowercased for consistency, split into 50-word chunks for granular retrieval, then passed through a local LLM (`tinyllama` via Ollama) to extract structured metadata: name, location, email, skills, experience, and job titles. A unique ID derived from that metadata ties all chunks back to the same candidate.

**Matching** — the job description goes through the same LLM extraction to pull out required skills and experience. ChromaDB then finds the most semantically similar chunks across the whole candidate pool. Chunks are grouped back to their source candidate, and a weighted hybrid score is computed: semantic similarity carries the most weight (0.5), followed by skills overlap (0.3) and experience fit (0.2). Candidates are ranked and the top N are returned.

**Reliability** — all LLM calls use exponential backoff retry logic. File uploads enforce a 2 MB size limit and format validation. Failures are caught per-file so a bad CV never blocks the rest of the batch.

---

## Stack

`FastAPI` · `ChromaDB` · `Ollama (tinyllama)` · `Streamlit` · `Pydantic v2` · `PyMuPDF` · `Docker Compose`

---

## Run it

```bash
# 1. Pull the model
ollama pull tinyllama && ollama serve

# 2. Clone and start
git clone https://github.com/rezaahmadi-99/job-cv-matcher.git
cd job-cv-matcher
docker compose up --build -d
```

Open **http://localhost:8501** to start uploading CVs.  
API docs at **http://localhost:8001/docs**.
