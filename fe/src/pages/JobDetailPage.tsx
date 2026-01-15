import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Briefcase, MapPin, Calendar, Users } from 'lucide-react'
import { useJob } from '@/hooks/useAPI'
import { formatDate } from '@/lib/utils'

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: job, isLoading, error } = useJob(id!)

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    )
  }

  if (error || !job) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">Failed to load job details</p>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <Link to="/jobs" className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-800 mb-6">
        <ArrowLeft size={20} />
        Back to Jobs
      </Link>

      <div className="bg-white border border-gray-200 rounded-lg p-8">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-4">{job.title}</h1>
            <div className="flex items-center gap-6 text-gray-600">
              {job.location && (
                <div className="flex items-center gap-2">
                  <MapPin size={18} />
                  {job.location}
                </div>
              )}
              <div className="flex items-center gap-2">
                <Calendar size={18} />
                {formatDate(job.created_at)}
              </div>
              {job.min_years_experience && (
                <div className="flex items-center gap-2">
                  <Briefcase size={18} />
                  {job.min_years_experience}+ years
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="prose max-w-none mb-8">
          <h2 className="text-xl font-semibold mb-4">Job Description</h2>
          <p className="text-gray-700 whitespace-pre-wrap">{job.description_raw}</p>
        </div>

        <div className="flex gap-4 pt-6 border-t">
          <Link
            to={`/matching?jobId=${job.id}`}
            className="btn btn-primary flex items-center gap-2"
          >
            <Users size={20} />
            Match Candidates
          </Link>
        </div>
      </div>
    </div>
  )
}
