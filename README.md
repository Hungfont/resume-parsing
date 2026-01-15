# Resume Matching MVP

Production-ready boilerplate for a Job → Candidates matching system with:
- Realtime resume upload (PDF/CSV/Excel with OCR)
- Multilingual embeddings (Vietnamese/English)
- Config-driven rule engine
- Full audit trails
- PostgreSQL + pgvector

## Features

- **Realtime Upload**: FastAPI endpoint for PDF/CSV/Excel resume processing
- **OCR**: Free/open-source OCR (Tesseract or Hugging Face models)
- **Embeddings**: sentence-transformers multilingual models
- **Skills**: Taxonomy-based extraction with rapidfuzz fuzzy matching
- **Rules**: Config-driven hard filters + soft scoring
- **Audit**: Full trace for every candidate-job match
- **Storage**: PostgreSQL + pgvector for efficient similarity search

## Architecture

```
├── ai/                  # AI/ML logic (embeddings, skills)
├── be/                  # Backend (DB, API, pipelines)
│   ├── pipelines/       # Processing pipelines
│   ├── api.py           # FastAPI endpoints
│   ├── models.py        # SQLAlchemy models
│   ├── rules.py         # Rule engine
│   ├── parsers.py       # Document parsing + OCR
│   └── config.py        # Pydantic settings
├── fe/                  # Frontend (placeholder)
├── instructions/        # Copilot instructions
├── requirements.txt     # Dependencies
└── main.py              # Entry point
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Tesseract (for OCR)

**Windows**:
```bash
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
# Install and add to PATH
```

**Ubuntu/Debian**:
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-vie
```

**macOS**:
```bash
brew install tesseract tesseract-lang
```

### 3. Setup PostgreSQL + pgvector

```bash
# Install PostgreSQL 16+
# Then install pgvector extension:
# CREATE EXTENSION vector;
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env with your database URL and settings
```

### 5. Initialize Database

```bash
# Using Alembic (to be added) or manually:
python -c "from be.models import Base; from be.db import engine; import asyncio; asyncio.run(engine.run_sync(Base.metadata.create_all))"
```

## Usage

### Start the API Server

```bash
python main.py
```

Or with uvicorn directly:
```bash
uvicorn be.api:app --reload --host 0.0.0.0 --port 8000
```

### Complete Workflow

**1. Upload candidate resumes:**

```bash
curl -X POST http://localhost:8000/upload-resume \
  -F "file=@resume.pdf" \
  -F "full_name=John Doe"
```

**2. Create a job posting:**

```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Senior Python Developer",
    "description": "Looking for Python expert with PostgreSQL. 3+ years required.",
    "min_years_experience": 3
  }'
```

**3. Run matching pipeline:**

```bash
curl -X POST http://localhost:8000/jobs/1/match \
  -H "Content-Type: application/json" \
  -d '{"top_n": 10}'
```

**4. Retrieve shortlist:**

```bash
curl http://localhost:8000/jobs/1/shortlist
```

### API Documentation

Visit http://localhost:8000/docs for interactive API documentation.

## Tech Stack (2026, Open-Source)

- **Language**: Python 3.12+
- **Database**: PostgreSQL 16+ with pgvector
- **Web**: FastAPI + Pydantic v2
- **Embeddings**: sentence-transformers (Hugging Face)
- **OCR**: Tesseract or HF models (TrOCR/Donut)
- **Skills**: rapidfuzz + taxonomy
- **Parsing**: pypdf, pdfplumber, pandas, openpyxl

## Configuration

All settings in `.env` or environment variables:

- `DB_URL`: PostgreSQL connection string
- `EMBEDDING_MODEL_NAME`: Hugging Face model ID
- `OCR_BACKEND`: "tesseract" or "hf"
- `MATCHING_TOP_K`, `MATCHING_TOP_N`: Retrieval/shortlist sizes
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

See `.env.example` for all options.

## Pipelines

### 1. Ingestion
- Parse file (PDF/CSV/Excel)
- Extract raw text (with OCR fallback)

### 2. Normalization
- Clean text (whitespace, punctuation)
- Preserve Vietnamese diacritics
- Remove URLs, optionally emails

### 3. Skill Extraction
- Taxonomy-based matching
- Synonym support
- Fuzzy matching (rapidfuzz)
- Evidence/span tracking

### 4. Embeddings
- sentence-transformers multilingual models
- Batch processing
- Cached model loading

### 5. Persistence
- Store candidates + metadata
- Store embeddings (pgvector)
- Store extracted skills with evidence

## Rule Engine

Config-driven rules in JSON/DB:

**Hard Rules** (filters):
- `skills_required`: Must-have skills
- `min_years`: Minimum experience
- `location_match`: Location requirements

**Soft Rules** (scoring):
- `skills_bonus`: Nice-to-have skills
- `years_bonus`: Experience bonus
- `location_bonus`: Location preference

All evaluations produce audit traces with evidence.

## Development

### Run Tests (to be added)
```bash
pytest
```

### Type Checking
```bash
mypy be/ ai/
```

### Code Formatting
```bash
black be/ ai/
ruff check be/ ai/
```

## License

MIT (or your preferred license)
