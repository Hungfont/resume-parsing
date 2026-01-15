export interface Candidate {
  id: number
  full_name: string
  name: string  // Alias for full_name
  resume_raw: string
  resume_normalized?: string
  location?: string
  years_experience?: number
  skills: Skill[]  // Add skills array
  metadata?: Record<string, any>
  created_at: string
  updated_at: string
  uploaded_at: string  // Alias for created_at
}

export interface Job {
  id: number
  title: string
  description: string  // Alias for description_raw
  description_raw: string
  description_normalized?: string
  location?: string
  remote_policy?: string
  min_years_experience?: number
  skills: Skill[]  // Add skills array
  metadata?: Record<string, any>
  created_at: string
  updated_at: string
}

export interface Skill {
  id?: number
  skill_name: string  // Add skill_name
  canonical_skill: string
  confidence: number
  evidence: string
}

export interface UploadResumeResponse {
  status: string
  candidate_id: number
  full_name: string
  skills_extracted: number
  skills: Skill[]
  embedding_dim: number
  message: string
}

export interface CreateJobRequest {
  title: string
  description: string
  location?: string
  remote_policy?: string
  min_years_experience?: number
  metadata?: Record<string, any>
}

export interface CreateJobResponse {
  status: string
  job_id: number
  title: string
  skills_extracted: number
  skills: Skill[]
  embedding_dim: number
  message: string
}

export interface RuleEvidence {
  source: string
  text: string
  span?: {
    start: number
    end: number
  }
}

export interface RuleTrace {
  rule_id: string
  name: string
  status: 'PASS' | 'FAIL' | 'SKIP'
  reason: string
  evidence: RuleEvidence[]
  score_delta: number
}

export interface MatchResult {
  candidate_id: number
  rank: number
  retrieval_similarity: number
  final_score: number
  rule_trace: RuleTrace[]
}

export interface MatchRequest {
  top_k?: number
  top_n?: number
  rules_version?: string
}

// Alias for MatchRequest
export type MatchParams = MatchRequest

export interface MatchResponse {
  status: string
  job_id: number
  top_n: number
  matches: MatchResult[]
  embedding_model_version: string
  taxonomy_version: string
  rules_version: string
  computed_at: string
  message: string
}

export interface ShortlistResponse {
  job_id: number
  top_n: number
  matches: MatchResult[]
  embedding_model_version: string
  taxonomy_version: string
  rules_version: string
  computed_at: string
  is_stale: boolean
}

export interface HealthResponse {
  status: string
  version: string
}

export interface ErrorResponse {
  error: string
  detail?: string
}
