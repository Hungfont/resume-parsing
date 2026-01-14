# Copilot Instructions: Job → Candidates Matching MVP

These instructions apply to **any AI agent or developer** working in this repository.
The project is an MVP for **Job → Candidates** matching, batch-first, realtime-ready later.

---

## 1. Project Scope & Goals

- **Primary goal**: For each job, produce a **shortlist of Top-N candidates**.
- **Matching direction (MVP)**: Only **Job → Candidates**.
- **Core behavior**:
  - Retrieve TopK candidates using **pgvector similarity**.
  - Apply **config-driven rules** (hard filters, then soft scoring).
  - Compute **final_score + rank** and **persist** to `job_shortlists`.
  - Every candidate in a shortlist MUST have an **audit trace**.

### Non-goals (MVP)
- Candidate → Jobs (this is Phase 2, do not implement unless explicitly requested).
- Deployment, infra, monitoring/observability.
- UI/front-end.

If in doubt, prefer **back-end logic, data modeling, and batch pipelines**, not UI or infra.

---

## 2. Hard Constraints (Do NOT Violate)

1. **Vector DB**
   - MUST use **PostgreSQL + pgvector** for embeddings.
   - No external vector databases (Pinecone, Weaviate, Milvus, etc.).

2. **Language**
   - Input data is **mixed Vietnamese/English**.
   - All NLP components (embeddings, skill extraction) must work reasonably for both.

3. **Skills in Free Text**
   - Skills come mainly from **unstructured text** (JD/resumes).
   - System MUST implement **skill extraction + canonicalization**:
     - Dictionary/taxonomy based.
     - Synonyms.
     - Regex where helpful.
     - Fuzzy matching (use **rapidfuzz**).

4. **Config-Driven Rules**
   - Business rules are defined by HR/job posters.
   - Rules MUST be **config-driven**, **versioned**, and **not hard-coded**.
   - Allowed sources: JSON/YAML files or DB tables.
   - Code can define the **rule engine**, but not hard-wire specific business rules.

5. **Async-first / Batch-first**
   - On-demand computation must **not block UI**.
   - Design around **stored shortlists** and **async refresh**.
   - For now, focus on batch pipelines; keep design **realtime-ready** (clear separation of compute vs. read APIs).

Any change that conflicts with these constraints should be rejected or flagged.

---

## 3. Tech Stack & Libraries (Defaults)

- **Language**: Python 3.11+
- **Database**: PostgreSQL 15/16 with **pgvector** extension.
- **Embeddings**: Hugging Face **sentence-transformers**.
  - Default model: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
- **Skill extraction**: taxonomy + synonyms + dictionary/regex + fuzzy matching via **rapidfuzz**.
- **API (only if/when needed)**: FastAPI.

When adding new components, stay aligned with this stack unless the user explicitly approves a deviation.

---

## 4. Core Data Model (Conceptual)

Model these **entities** and **derived artifacts** in PostgreSQL.

### 4.1 Base entities

- `jobs`
  - `id`
  - `title`
  - `description_raw` (original JD text)
  - `description_normalized`
  - `location`, `remote_policy`
  - `min_years_experience`
  - `metadata` (JSONB; e.g., domain, salary range)
  - timestamps

- `candidates`
  - `id`
  - `full_name`
  - `resume_raw`
  - `resume_normalized`
  - `location`
  - `years_experience`
  - `metadata` (JSONB; domains, education, etc.)
  - timestamps

### 4.2 Skill extraction

- `extracted_skills_jobs`
  - `id`
  - `job_id`
  - `canonical_skill`
  - `raw_text`
  - `confidence`
  - `evidence_text`
  - `span_start`, `span_end`
  - `taxonomy_version`

- `extracted_skills_candidates`
  - `id`
  - `candidate_id`
  - `canonical_skill`
  - `raw_text`
  - `confidence`
  - `evidence_text`
  - `span_start`, `span_end`
  - `taxonomy_version`

### 4.3 Embeddings (pgvector)

- `job_embeddings`
  - `job_id`
  - `embedding` (pgvector, e.g., `vector(384)`)
  - `embedding_model`
  - `embedding_model_version`
  - `computed_at`

- `candidate_embeddings`
  - `candidate_id`
  - `embedding` (pgvector)
  - `embedding_model`
  - `embedding_model_version`
  - `computed_at`

### 4.4 Rules & taxonomy

- `rules_config`
  - `id`
  - `rules_version` (e.g., `v1.0.0`)
  - `scope` (global / per-job-type / per-tenant)
  - `rules_json` (JSON)
  - `created_at`

- `skill_taxonomy`
  - `id`
  - `canonical_skill`
  - `synonyms` (array/text/JSON)
  - `category`
  - `taxonomy_version`

### 4.5 Shortlists (critical)

- `job_shortlists`
  - `id`
  - `job_id`
  - `candidate_id`
  - `rank` (1..N)
  - `retrieval_similarity` (float)
  - `final_score` (float)
  - `rule_trace` (JSONB, see section 6)
  - `embedding_model_version`
  - `taxonomy_version`
  - `rules_version`
  - `computed_at`
  - `is_stale` (bool; for realtime-ready plan)

Do **not** remove these fields when designing schemas; you may refine names and types but must preserve semantics.

---

## 5. Matching & Scoring Logic

**High-level workflow for each job:**

1. Retrieve job embedding from `job_embeddings`.
2. Query `candidate_embeddings` via pgvector to get **TopK** similar candidates (K ≫ N, e.g., 300–1000).
3. Apply **hard rules** to filter out candidates.
4. Apply **soft rules** to adjust scores.
5. Combine similarity + rule-based signals to compute **final_score**.
6. Sort by `final_score` and produce **TopN**.
7. Persist to `job_shortlists` including full **rule_trace** and version info.

### 5.1 Retrieval (pgvector)

Use cosine similarity (or equivalent) via pgvector. Example pattern (pseudo-SQL):

```sql
SELECT candidate_id,
       1 - (embedding <=> :job_embedding) AS similarity
FROM candidate_embeddings
ORDER BY embedding <=> :job_embedding
LIMIT :top_k;
```

### 5.2 Rule evaluation

- **Hard constraints** (filtering): if any fails, the candidate is **excluded** from the shortlist.
  - Examples: must-have skills, location/remote policy, minimum years of experience, education.
- **Soft constraints** (scoring): adjust a base score (from similarity) with bonuses/penalties.
  - Examples: nice-to-have skills, domain boosts, seniority, language fluency.

All evaluations must be **deterministic** and driven by **rules_config**.

---

## 6. Rule Engine & Audit Requirements

### 6.1 Rule configuration model (JSON example)

Rules should be represented in a structured, versioned form, for example:

```json
{
  "rules_version": "v1.0.0",
  "hard_rules": [
    {
      "id": "must_have_skills",
      "name": "Must-have skills",
      "type": "skills_required",
      "params": {
        "all_of": ["Python", "PostgreSQL"],
        "min_confidence": 0.7
      }
    },
    {
      "id": "min_years_experience",
      "name": "Minimum years of experience",
      "type": "min_years",
      "params": {
        "min": 3
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

The engine must interpret `type` and `params` generically; do **not** hard-code specific job rules.

### 6.2 Rule trace format (MANDATORY)

For every candidate in a shortlist, store a `rule_trace` array like:

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
    },
    {
      "rule_id": "nice_to_have_skills",
      "name": "Nice-to-have skills",
      "status": "PASS",
      "reason": "Candidate has FastAPI (1 nice-to-have skill)",
      "evidence": [
        {
          "source": "candidate_resume",
          "text": "Experience building APIs with FastAPI",
          "span": {"start": 220, "end": 260}
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

**Never** return or store shortlist entries **without** `rule_trace` and version fields.

The system must be able to explain **“why not matched”** by referencing failed hard rules in the trace (even if candidate is filtered before shortlist, the reason should be derivable from evaluation logic).

---

## 7. Batch-First Workflow

Implement and optimize this workflow **first**:

1. **Ingest jobs + candidates**
   - Insert/update records in `jobs` and `candidates`.

2. **Normalize text**
   - Clean raw JD/resume text (lowercasing, whitespace, punctuation, language-agnostic normalization).
   - Handle Vietnamese diacritics carefully (avoid losing meaning).

3. **Extract skills + evidence**
   - Use `skill_taxonomy` + synonyms + regex + rapidfuzz.
   - Store canonical skills and evidence in `extracted_skills_*` tables.

4. **Compute embeddings + store in pgvector**
   - Use `paraphrase-multilingual-MiniLM-L12-v2` by default.
   - Batch processing with GPU/CPU as available.
   - Store vectors in `job_embeddings` and `candidate_embeddings`.

5. **Match per job**
   - Retrieve TopK candidates via pgvector.
   - Apply rules (hard first, then soft).
   - Compute `final_score`, assign `rank`.
   - Persist TopN shortlist with full audit trail to `job_shortlists`.

Keep the pipeline modular: each step should be callable independently (for future realtime updates).

---

## 8. Realtime-Ready Design (Plan Only for Now)

Do **not** fully implement realtime infra unless explicitly requested, but design code to support:

- **On JobUpdated/CandidateUpdated**:
  - Recompute skills + embeddings for that single entity.
  - Mark affected shortlists as `is_stale = true`.

- **Stale-while-revalidate**:
  - Read APIs return stored shortlist immediately.
  - Include `is_stale` and `computed_at`.
  - A background worker recomputes shortlists when stale or when `rules_version` changes.

Focus current coding on clean boundaries: ingestion, feature extraction, embeddings, matching, and shortlist persistence.

---

## 9. Coding Guidelines for Agents

When writing or modifying code in this repo:

- **Respect constraints** in sections 2–8; do not introduce conflicting patterns.
- Prefer **clear, modular Python**:
  - Separate concerns: extraction, embeddings, rules, persistence.
  - Use dependency injection / configuration where useful (e.g., model name, TopK/N).
- Avoid over-engineering: this is an **MVP**, but the design must remain clean and extensible.
- Do **not** add UI or heavy infra code unless requested.
- When adding APIs (if asked):
  - Use FastAPI.
  - Make responses **JSON DTOs** that always include audit fields for shortlist items.

### 9.1 Testing & validation

- For new logic (e.g., rule evaluation, skill matcher), add unit tests when possible.
- Prefer deterministic tests: fixed inputs, fixed outputs.
- If tests cannot be added (timeboxed), at least provide clear sample usage.

### 9.2 When uncertain

If you are unsure about:
- **Data schema specifics** (additional fields, types),
- **Rule definitions** (new rule types, thresholds),
- **TopN/TopK values**, or
- **Required hard constraints**, 

**ask the user for clarification** instead of guessing.

---

## 10. Example Shortlist Response DTO

When an API or batch job outputs shortlists, follow a structured format similar to:

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

**Never** omit `rule_trace` or versioning metadata from shortlist responses.

---

## 11. Summary for Agents (Quick Checklist)

Before you write code, verify:

- [ ] You are implementing **Job → Candidates** matching only.
- [ ] You are using **PostgreSQL + pgvector** for embeddings.
- [ ] You support **Vietnamese + English** in text handling.
- [ ] Skills are extracted from free text and **canonicalized** using taxonomy + rapidfuzz.
- [ ] Business rules are **config-driven** and **versioned**, not hard-coded.
- [ ] Matching uses **TopK via pgvector**, then **rules**, then **TopN shortlist**.
- [ ] Every shortlist item includes **similarity, final_score, rank, rule_trace, versions, computed_at**.
- [ ] Design is **batch-first** but leaves a clear path for realtime updates.

If any of these are not true for the change you are about to make, stop and adjust the design.
