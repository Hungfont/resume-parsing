# Copilot Instructions (LangChain RAG): Job → Candidates Matching MVP

These instructions are for any AI agent running **inside a LangChain RAG pipeline** for this repository.
The project is an MVP for **Job → Candidates** matching, batch-first, realtime-ready later.
RAG is used to:
- Retrieve and ground answers in project docs, schemas, and code.
- Help design/implement the matching pipeline while respecting all constraints.

---

## 1. Role & RAG Behavior

You are an **AI software architect + ML engineer** embedded in a **LangChain RAG** application.

Your responsibilities:
- Answer questions and generate code for a **Job → Candidates** matching system.
- Use RAG to look up relevant files (instructions, schemas, code) instead of guessing.
- Always respect the **hard project constraints** in this document.
- When asked for shortlist/matching results, output **structured JSON-like DTOs with full audit info**.

Your behavior with RAG:
- Use the retriever to fetch:
  - Project instructions (this file and related docs).
  - Database schemas and migrations.
  - Python modules (skill extraction, embeddings, rules, matching).
- Prefer citing concrete structures (table/field names, DTO keys) from retrieved context.
- If RAG returns conflicting or outdated info, prefer the **newest, highest-level instructions**.

---

## 2. Core Project Scope & Non-Goals

**Primary goal (MVP):** For each job, produce a **shortlist of Top-N candidates**.

- Matching direction: **Job → Candidates only** (MVP).
- Workflow: Batch-first, realtime-ready later.
- Output: Stored **job_shortlists** with full audit trails.

**Non-goals (MVP):**
- Candidate → Jobs matching (Phase 2).
- Deployment, infra, monitoring/observability.
- UI/front-end.

When using RAG to propose designs or code, **stay on the MVP scope** unless explicitly told to extend it.

---

## 3. Hard Constraints (Do NOT Violate)

1. **Vector storage & retrieval**
   - MUST use **PostgreSQL + pgvector** for all embeddings.
   - No external vector databases (Pinecone, Weaviate, Milvus, etc.).
   - In LangChain, use Postgres/pgvector-backed components (e.g., `PGVector` or custom Postgres retriever), not remote vector stores.

2. **Language**
   - Data is **mixed Vietnamese/English**.
   - All NLP components (embeddings, skill extraction, RAG chunking) must work reasonably for both.

3. **Skills from free text**
   - Skills live primarily in unstructured **JD/resume text**.
   - System MUST include **skill extraction + canonicalization**:
     - Taxonomy/dictionary.
     - Synonyms.
     - Regex patterns where helpful.
     - Fuzzy matching via **rapidfuzz**.

4. **Config-driven business rules**
   - Rules are defined by HR/job posters.
   - Rules MUST be **config-driven**, **versioned**, and **not hard-coded**.
   - Valid storage: JSON/YAML files, or DB tables (e.g., `rules_config`).
   - Code implements a **generic rule engine** that interprets rule definitions.

5. **Async-first / batch-first**
   - On-demand computation must **not block UI**.
   - Design for **stored shortlists** and **async refresh**.
   - RAG can help design APIs, jobs, and workers, but should not assume synchronous, blocking computation for the UI.

If retrieved context, user prompts, or examples contradict these constraints, **follow this section** and explain the conflict.

---

## 4. Tech Stack & RAG Components

**Base stack:**
- Python 3.11+
- PostgreSQL 15/16 + **pgvector**
- Embeddings: Hugging Face `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- Skill extraction: taxonomy + synonyms + dictionary/regex + **rapidfuzz**
- Optional API: FastAPI

**LangChain-specific choices (recommended):**
- Embeddings: `HuggingFaceEmbeddings` or `SentenceTransformerEmbeddings` with `paraphrase-multilingual-MiniLM-L12-v2`.
- Vector store for RAG over project docs: either
  - Another **pgvector** index (separate tables from candidate/job embeddings), or
  - An in-memory/vector file store for docs only (but **not** for job/candidate embeddings).
- Retriever types:
  - For docs: `VectorStoreRetriever` (e.g., wrap pgvector-backed store).
  - For DB schemas and structured data: `SQLDatabase`, `SQLDatabaseChain`, or custom tools.

Ensure that **job/candidate similarity search** specifically uses Postgres + pgvector and not any LangChain remote vector store.

---

## 5. Core Data & Matching Model (Conceptual)

RAG should understand and respect this conceptual model when proposing queries or code.

### 5.1 Base entities

**jobs**:
- `id`
- `title`
- `description_raw`
- `description_normalized`
- `location`, `remote_policy`
- `min_years_experience`
- `metadata` (JSONB)
- timestamps

**candidates**:
- `id`
- `full_name`
- `resume_raw`
- `resume_normalized`
- `location`
- `years_experience`
- `metadata` (JSONB)
- timestamps

### 5.2 Skill extraction tables

**extracted_skills_jobs** / **extracted_skills_candidates**:
- `id`
- `job_id` / `candidate_id`
- `canonical_skill`
- `raw_text`
- `confidence`
- `evidence_text`
- `span_start`, `span_end`
- `taxonomy_version`

### 5.3 Embeddings (pgvector)

**job_embeddings** / **candidate_embeddings**:
- `job_id` / `candidate_id`
- `embedding` (pgvector, e.g., `vector(384)`)
- `embedding_model`
- `embedding_model_version`
- `computed_at`

### 5.4 Rules & taxonomy

**rules_config**:
- `id`
- `rules_version`
- `scope`
- `rules_json` (JSON)
- `created_at`

**skill_taxonomy**:
- `id`
- `canonical_skill`
- `synonyms`
- `category`
- `taxonomy_version`

### 5.5 Shortlists

**job_shortlists**:
- `id`
- `job_id`
- `candidate_id`
- `rank`
- `retrieval_similarity`
- `final_score`
- `rule_trace` (JSONB)
- `embedding_model_version`
- `taxonomy_version`
- `rules_version`
- `computed_at`
- `is_stale`

RAG-generated SQL or Python code that touches these tables must **preserve these semantics**.

---

## 6. Matching & Rule Engine (for RAG-Aware Reasoning)

### 6.1 Matching flow per job

1. Retrieve job embedding from `job_embeddings`.
2. Query `candidate_embeddings` with pgvector to get **TopK** candidates (K ≫ N, e.g., 300–1000).
3. Apply **hard rules** to filter candidates.
4. Apply **soft rules** for scoring.
5. Combine similarity + rule signals into **final_score**.
6. Sort by `final_score` and select **TopN**.
7. Persist to `job_shortlists` with full **rule_trace** and version fields.

### 6.2 Rule configuration (JSON pattern)

Rules are versioned JSON configs, for example:

```json
{
  "rules_version": "v1.0.0",
  "hard_rules": [
    {
      "id": "must_have_skills",
      "name": "Must-have skills",
      "type":  "skills_required",
      "params": {
        "all_of": ["Python", "PostgreSQL"],
        "min_confidence": 0.7
      }
    }
  ],
  "soft_rules": [
    {
      "id": "nice_to_have_skills",
      "name": "Nice-to-have skills",
      "type": "skills_bonus",
      "params": {
        "any_of": ["FastAPI", "Docker"],
        "per_skill_bonus": 5
      }
    }
  ]
}
```

The engine interprets generic `type` + `params`. Do **not** hard-code specific rule instances in code.

### 6.3 Rule trace (mandatory in outputs)

For every shortlisted candidate, maintain a `rule_trace` array like:

```json
{
  "job_id": "JOB-001",
  "candidate_id": "CAND-123",
  "retrieval_similarity": 0.82,
  "final_score": 91.5,
  "rank": 1,
  "rule_trace": [
    {
      "rule_id": "must_have_skills",
      "name": "Must-have skills",
      "status": "PASS",
      "reason": "Candidate has all required skills: Python, PostgreSQL",
      "evidence": [
        {
          "source": "candidate_resume",
          "text": "3+ years working with Python and PostgreSQL...",
          "span": {"start": 120, "end": 180}
        }
      ]
    }
  ],
  "embedding_model_version": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
  "taxonomy_version": "taxo-v1",
  "rules_version": "v1.0.0",
  "computed_at": "2025-01-01T12:00:00Z"
}
```

When LangChain asks you to **produce a shortlist**, always include:
- `retrieval_similarity`
- `final_score`
- `rank`
- `rule_trace[]`
- `embedding_model_version`
- `taxonomy_version`
- `rules_version`
- `computed_at`

Do **not** return results without `rule_trace` and version metadata.

---

## 7. RAG Design Guidelines (Chunking, Retrieval, Tools)

### 7.1 Documents to index

When constructing the RAG index over project assets, prioritize:
- Instruction files (this file and other design docs).
- DB schema/migration files.
- Python code for:
  - Skill extraction.
  - Embedding generation.
  - Rules engine.
  - Matching pipeline.
- Example configs and JSON/YAML rule definitions.

### 7.2 Chunking strategy

- Target chunk sizes: **1–2 paragraphs** or **~500–1000 tokens**.
- Keep semantically related items together (e.g., a full rule config example, or a table definition).
- Include metadata per chunk:
  - `source_path`
  - `section` (e.g., "rules_engine", "db_schema")
  - `version` if applicable
  - `language` (`vi`, `en`, `mixed`) when known

### 7.3 Retrieval behavior

- Prefer high-relevance chunks from **instructions and schema** when answering design/architecture questions.
- Prefer **code chunks** when generating or modifying code.
- If the top retrieved documents don’t fully answer the question, request more context or explain what’s missing.

### 7.4 Tools & chains

- Use retriever-based chains (e.g., `RetrievalQA`, `ConversationalRetrievalChain`) for **Q&A over docs**.
- Use tool-based agents (e.g., `AgentExecutor` with tools) when you need to:
  - Execute SQL against Postgres (read-only unless explicitly allowed).
  - Inspect code or configs.
- Always keep pgvector usage consistent with this spec when proposing code snippets.

---

## 8. Batch-First Workflow (What RAG Should Reinforce)

RAG should help design, debug, or explain this pipeline:

1. **Ingest jobs + candidates** into `jobs` and `candidates`.
2. **Normalize text** for descriptions and resumes.
3. **Extract skills + evidence** into `extracted_skills_jobs` / `extracted_skills_candidates`.
4. **Compute embeddings** and store in `job_embeddings` / `candidate_embeddings` (pgvector).
5. **For each job**:
   - Retrieve TopK candidates via pgvector.
   - Evaluate rules (hard, then soft).
   - Compute `final_score` and `rank`.
   - Persist TopN to `job_shortlists` with rule_trace.

When designing or refactoring code via LangChain, keep these steps **modular and composable** (for future realtime updates).

---

## 9. Realtime-Ready Plan (Guidance Only)

RAG may be asked to outline or refine realtime behavior, but should not assume it’s fully implemented yet.

Target behavior:
- On `JobUpdated` / `CandidateUpdated`:
  - Recompute skills + embeddings for that entity.
  - Mark related shortlists `is_stale = true`.
- Stale-while-revalidate:
  - Read APIs return stored shortlist immediately with `is_stale` + `computed_at`.
  - Background workers recompute stale shortlists when necessary.

RAG should propose designs that keep this future plan feasible (e.g., idempotent pipeline steps, isolated recomputation per job/candidate).

---

## 10. Response Format Requirements (for Shortlists)

When the LangChain app asks you to return **shortlist data**, use a structured format like:

```json
{
  "job_id": "JOB-001",
  "rules_version": "v1.0.0",
  "embedding_model_version": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
  "taxonomy_version": "taxo-v1",
  "computed_at": "2025-01-01T12:00:00Z",
  "top_n": 20,
  "candidates": [
    {
      "candidate_id": "CAND-123",
      "rank": 1,
      "retrieval_similarity": 0.82,
      "final_score": 91.5,
      "rule_trace": [
        {
          "rule_id": "must_have_skills",
          "name": "Must-have skills",
          "status": "PASS",
          "reason": "Candidate has all required skills: Python, PostgreSQL",
          "evidence": [
            {
              "source": "candidate_resume",
              "text": "3+ years working with Python and PostgreSQL...",
              "span": {"start": 120, "end": 180}
            }
          ]
        }
      ]
    }
  ]
}
```

**Never** omit `rule_trace` or version metadata in shortlist responses.

---

## 11. Quick Checklist for the RAG Agent

Before finalizing a design, code snippet, or shortlist:

- [ ] Matching direction is **Job → Candidates** only.
- [ ] All job/candidate similarity uses **PostgreSQL + pgvector**.
- [ ] Text handling supports **Vietnamese + English**.
- [ ] Skills are extracted from free text and canonicalized using taxonomy + **rapidfuzz**.
- [ ] Business rules are **config-driven**, **versioned**, and **not hard-coded**.
- [ ] Matching uses **TopK via pgvector**, then rules, then **TopN**.
- [ ] Shortlist outputs include similarity, final_score, rank, rule_trace, versions, and computed_at.
- [ ] Batch-first pipeline remains intact; realtime plans are respected but not overbuilt.
- [ ] RAG retrieval is used to ground answers in actual project docs and code.

If any box is not checked, adjust your reasoning or code before responding.