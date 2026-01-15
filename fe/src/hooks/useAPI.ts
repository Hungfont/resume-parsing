import useSWR from 'swr'
import { fetcher } from '@/lib/fetcher'
import type {
  Candidate,
  Job,
  MatchResponse,
} from '@/types/api'

// Candidates
export function useCandidates() {
  return useSWR<Candidate[]>('/candidates', fetcher)
}

export function useCandidate(id: number) {
  return useSWR<Candidate>(id ? `/candidates/${id}` : null, fetcher)
}

// Jobs
export function useJobs() {
  return useSWR<Job[]>('/jobs', fetcher)
}

export function useJob(id: number | string) {
  return useSWR<Job>(id ? `/jobs/${id}` : null, fetcher)
}

// Matching
export function useShortlist(jobId: number) {
  return useSWR<MatchResponse>(
    jobId ? `/jobs/${jobId}/shortlist` : null,
    fetcher
  )
}
