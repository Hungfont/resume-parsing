import { Link } from 'react-router-dom'
import { Briefcase, Plus, Calendar, MapPin } from 'lucide-react'
import { useJobs } from '@/hooks/useAPI'
import { formatDate } from '@/lib/utils'

export default function JobsPage() {
  const { data: jobs, isLoading, error } = useJobs()

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">Failed to load jobs: {error.message}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Job Openings</h1>
        <Link
          to="/jobs/create"
          className="btn btn-primary flex items-center gap-2"
        >
          <Plus size={20} />
          Create Job
        </Link>
      </div>

      {!jobs || jobs.length === 0 ? (
        <div className="text-center py-12">
          <Briefcase size={48} className="mx-auto text-gray-400 mb-4" />
          <p className="text-gray-600 mb-4">No jobs posted yet</p>
          <Link to="/jobs/create" className="btn btn-primary">
            Create First Job
          </Link>
        </div>
      ) : (
        <div className="grid gap-4">
          {jobs.map((job) => (
            <Link
              key={job.id}
              to={`/jobs/${job.id}`}
              className="block bg-white border border-gray-200 rounded-lg p-6 hover:shadow-lg transition-shadow"
            >
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">
                    {job.title}
                  </h3>
                  <div className="flex items-center gap-4 text-sm text-gray-600">
                    {job.location && (
                      <div className="flex items-center gap-1">
                        <MapPin size={16} />
                        {job.location}
                      </div>
                    )}
                    <div className="flex items-center gap-1">
                      <Calendar size={16} />
                      {formatDate(job.created_at)}
                    </div>
                  </div>
                </div>
                {job.min_years_experience && (
                  <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
                    {job.min_years_experience}+ years
                  </span>
                )}
              </div>
              <p className="text-gray-700 line-clamp-2">
                {job.description_raw}
              </p>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
