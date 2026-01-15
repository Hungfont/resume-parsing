'use client'

import { useState, Suspense } from 'react'
import { useSearchParams } from 'react-router-dom'
import { GitCompare, CheckCircle, XCircle, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react'
import { postData } from '@/lib/fetcher'
import { formatScore, formatPercentage, formatDate } from '@/lib/utils'
import type { MatchResponse, MatchResult, RuleTrace, MatchParams } from '@/types/api'

function MatchingContent() {
  const [searchParams] = useSearchParams()
  const jobIdParam = searchParams.get('jobId')

  const [jobId, setJobId] = useState<string>(jobIdParam || '')
  const [topK, setTopK] = useState<string>('500')
  const [topN, setTopN] = useState<string>('50')
  const [matching, setMatching] = useState(false)
  const [result, setResult] = useState<MatchResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [expandedMatch, setExpandedMatch] = useState<number | null>(null)

  const handleMatch = async () => {
    if (!jobId) {
      setError('Please enter a Job ID')
      return
    }

    setMatching(true)
    setError(null)
    setResult(null)

    try {
      const params: MatchParams = {
        top_k: topK ? parseInt(topK) : undefined,
        top_n: topN ? parseInt(topN) : undefined,
      }
      
      const response = await postData<MatchResponse>(
        `/jobs/${parseInt(jobId)}/match`,
        params
      )
      setResult(response)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Matching failed')
    } finally {
      setMatching(false)
    }
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Job → Candidates Matching
        </h1>
        <p className="text-gray-600">
          Run matching pipeline with pgvector retrieval and rule-based scoring
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <div className="card sticky top-20">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Matching Configuration
            </h2>

            <div className="space-y-4">
              <div>
                <label className="label">
                  Job ID <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  value={jobId}
                  onChange={(e) => setJobId(e.target.value)}
                  placeholder="e.g., 1"
                  className="input"
                  disabled={matching}
                />
              </div>

              <div>
                <label className="label">
                  Top K (Initial Retrieval)
                </label>
                <input
                  type="number"
                  value={topK}
                  onChange={(e) => setTopK(e.target.value)}
                  placeholder="500"
                  className="input"
                  disabled={matching}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Number of candidates to retrieve via pgvector
                </p>
              </div>

              <div>
                <label className="label">
                  Top N (Final Shortlist)
                </label>
                <input
                  type="number"
                  value={topN}
                  onChange={(e) => setTopN(e.target.value)}
                  placeholder="50"
                  className="input"
                  disabled={matching}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Number of top candidates after rule evaluation
                </p>
              </div>

              <button
                onClick={handleMatch}
                disabled={matching || !jobId}
                className="btn btn-primary w-full py-3 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <GitCompare className="h-5 w-5 mr-2" />
                {matching ? 'Running Matching...' : 'Run Matching'}
              </button>

              {error && (
                <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
                  <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              )}
            </div>

            <div className="mt-6 pt-6 border-t border-gray-200">
              <h3 className="font-medium text-gray-900 mb-2 text-sm">
                Matching Pipeline
              </h3>
              <ul className="text-xs text-gray-600 space-y-2">
                <li className="flex gap-2">
                  <span>1.</span>
                  <span>Retrieve job embedding (384-dim)</span>
                </li>
                <li className="flex gap-2">
                  <span>2.</span>
                  <span>Query pgvector for TopK similar candidates</span>
                </li>
                <li className="flex gap-2">
                  <span>3.</span>
                  <span>Apply hard rules (filters)</span>
                </li>
                <li className="flex gap-2">
                  <span>4.</span>
                  <span>Apply soft rules (scoring)</span>
                </li>
                <li className="flex gap-2">
                  <span>5.</span>
                  <span>Sort by final_score and select TopN</span>
                </li>
                <li className="flex gap-2">
                  <span>6.</span>
                  <span>Persist with full audit trail</span>
                </li>
              </ul>
            </div>
          </div>
        </div>

        <div className="lg:col-span-2">
          {result ? (
            <div className="space-y-6">
              <div className="card">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">
                  Matching Results
                </h2>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                  <div className="p-3 bg-blue-50 rounded-lg">
                    <p className="text-sm text-gray-600 mb-1">Job ID</p>
                    <p className="text-lg font-bold text-gray-900">{result.job_id}</p>
                  </div>
                  <div className="p-3 bg-green-50 rounded-lg">
                    <p className="text-sm text-gray-600 mb-1">Matches Found</p>
                    <p className="text-lg font-bold text-gray-900">{result.top_n}</p>
                  </div>
                  <div className="p-3 bg-purple-50 rounded-lg">
                    <p className="text-sm text-gray-600 mb-1">Rules Version</p>
                    <p className="text-lg font-bold text-gray-900">{result.rules_version}</p>
                  </div>
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-600 mb-1">Computed</p>
                    <p className="text-xs font-medium text-gray-900">
                      {formatDate(result.computed_at)}
                    </p>
                  </div>
                </div>

                <div className="text-sm text-gray-600 space-y-1 p-3 bg-gray-50 rounded-lg">
                  <p><strong>Model:</strong> {result.embedding_model_version}</p>
                  <p><strong>Taxonomy:</strong> {result.taxonomy_version}</p>
                </div>
              </div>

              <div className="space-y-4">
                {result.matches.map((match) => (
                  <MatchCard
                    key={match.candidate_id}
                    match={match}
                    expanded={expandedMatch === match.candidate_id}
                    onToggle={() =>
                      setExpandedMatch(
                        expandedMatch === match.candidate_id
                          ? null
                          : match.candidate_id
                      )
                    }
                  />
                ))}
              </div>
            </div>
          ) : (
            <div className="card text-center py-16">
              <GitCompare className="h-16 w-16 mx-auto mb-4 text-gray-400" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No Results Yet
              </h3>
              <p className="text-gray-600 mb-4">
                Enter a Job ID and run matching to see results
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function MatchCard({
  match,
  expanded,
  onToggle,
}: {
  match: MatchResult
  expanded: boolean
  onToggle: () => void
}) {
  const topScore = match.final_score >= 80
  const goodScore = match.final_score >= 60 && match.final_score < 80

  return (
    <div className="card">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <div
              className={`
                h-10 w-10 rounded-full flex items-center justify-center font-bold text-white
                ${topScore ? 'bg-green-500' : goodScore ? 'bg-yellow-500' : 'bg-gray-400'}
              `}
            >
              #{match.rank}
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                Candidate #{match.candidate_id}
              </h3>
              <p className="text-sm text-gray-600">
                Similarity: {formatPercentage(match.retrieval_similarity)}
              </p>
            </div>
          </div>
        </div>

        <div className="text-right">
          <div className="text-2xl font-bold text-gray-900">
            {formatScore(match.final_score)}
          </div>
          <p className="text-xs text-gray-600">Final Score</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="p-3 bg-gray-50 rounded-lg">
          <p className="text-xs text-gray-600 mb-1">Rank</p>
          <p className="font-semibold text-gray-900">#{match.rank}</p>
        </div>
        <div className="p-3 bg-blue-50 rounded-lg">
          <p className="text-xs text-gray-600 mb-1">Similarity</p>
          <p className="font-semibold text-gray-900">
            {formatPercentage(match.retrieval_similarity)}
          </p>
        </div>
        <div className="p-3 bg-purple-50 rounded-lg">
          <p className="text-xs text-gray-600 mb-1">Rules Evaluated</p>
          <p className="font-semibold text-gray-900">{match.rule_trace.length}</p>
        </div>
      </div>

      <button
        onClick={onToggle}
        className="flex items-center justify-between w-full p-3 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors"
      >
        <span className="font-medium text-gray-900">
          View Rule Evaluation Trace
        </span>
        {expanded ? (
          <ChevronUp className="h-5 w-5 text-gray-600" />
        ) : (
          <ChevronDown className="h-5 w-5 text-gray-600" />
        )}
      </button>

      {expanded && (
        <div className="mt-4 space-y-3">
          {match.rule_trace.map((trace, index) => (
            <RuleTraceCard key={index} trace={trace} />
          ))}
        </div>
      )}
    </div>
  )
}

function RuleTraceCard({ trace }: { trace: RuleTrace }) {
  const isPassed = trace.status === 'PASS'
  const isFailed = trace.status === 'FAIL'

  return (
    <div
      className={`
        p-4 rounded-lg border-2
        ${isPassed ? 'bg-green-50 border-green-200' : ''}
        ${isFailed ? 'bg-red-50 border-red-200' : ''}
        ${!isPassed && !isFailed ? 'bg-gray-50 border-gray-200' : ''}
      `}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          {isPassed && <CheckCircle className="h-5 w-5 text-green-600" />}
          {isFailed && <XCircle className="h-5 w-5 text-red-600" />}
          <div>
            <h4 className="font-semibold text-gray-900">{trace.name}</h4>
            <p className="text-xs text-gray-600">{trace.rule_id}</p>
          </div>
        </div>
        {trace.score_delta !== 0 && (
          <div
            className={`
              px-2 py-1 rounded text-sm font-medium
              ${trace.score_delta > 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}
            `}
          >
            {trace.score_delta > 0 ? '+' : ''}{trace.score_delta.toFixed(1)}
          </div>
        )}
      </div>

      <p className="text-sm text-gray-700 mb-3">{trace.reason}</p>

      {trace.evidence.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-gray-600">Evidence:</p>
          {trace.evidence.map((evidence, index) => (
            <div
              key={index}
              className="p-2 bg-white rounded border border-gray-200"
            >
              <p className="text-xs text-gray-600 mb-1">{evidence.source}</p>
              <p className="text-sm text-gray-800">{evidence.text}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function MatchingPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><p>Loading...</p></div>}>
      <MatchingContent />
    </Suspense>
  )
}
