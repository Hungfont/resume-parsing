import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { CheckCircle, AlertCircle } from 'lucide-react'
import { postData } from '@/lib/fetcher'
import { useSWRConfig } from 'swr'
import type { CreateJobRequest, CreateJobResponse } from '@/types/api'

type FormData = CreateJobRequest

export default function CreateJobPage() {
  const navigate = useNavigate()
  const { mutate } = useSWRConfig()
  const [creating, setCreating] = useState(false)
  const [result, setResult] = useState<CreateJobResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<FormData>()

  const onSubmit = async (data: FormData) => {
    setCreating(true)
    setError(null)

    try {
      const response = await postData<CreateJobResponse>('/jobs', data)
      setResult(response)
      
      // Revalidate jobs list
      mutate('/jobs')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create job')
    } finally {
      setCreating(false)
    }
  }

  const handleReset = () => {
    reset()
    setResult(null)
    setError(null)
  }

  if (result) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="card">
          <div className="flex items-center gap-3 mb-6">
            <div className="h-12 w-12 rounded-full bg-green-100 flex items-center justify-center">
              <CheckCircle className="h-6 w-6 text-green-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Job Created Successfully!
              </h1>
              <p className="text-gray-600">Job posting processed and stored</p>
            </div>
          </div>

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 p-4 bg-gray-50 rounded-lg">
              <div>
                <p className="text-sm text-gray-600 mb-1">Job ID</p>
                <p className="font-medium text-gray-900">{result.job_id}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-1">Title</p>
                <p className="font-medium text-gray-900">{result.title}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-1">Skills Extracted</p>
                <p className="font-medium text-gray-900">{result.skills_extracted}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-1">Embedding Dimension</p>
                <p className="font-medium text-gray-900">{result.embedding_dim}</p>
              </div>
            </div>

            {result.skills.length > 0 && (
              <div>
                <h3 className="font-semibold text-gray-900 mb-3">
                  Required Skills Detected
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {result.skills.map((skill, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-3 bg-green-50 rounded-lg"
                    >
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">
                          {skill.canonical_skill}
                        </p>
                        <p className="text-xs text-gray-600 mt-1 truncate">
                          {skill.evidence}
                        </p>
                      </div>
                      <div className="ml-3 px-2 py-1 bg-green-100 rounded text-sm font-medium text-green-700">
                        {(skill.confidence * 100).toFixed(0)}%
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex gap-3 pt-4">
              <button
                onClick={() => navigate(`/matching?jobId=${result.job_id}`)}
                className="btn btn-primary px-6 py-2"
              >
                Run Matching Now
              </button>
              <button
                onClick={handleReset}
                className="btn btn-outline px-6 py-2"
              >
                Create Another Job
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-3xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Create Job Posting
        </h1>
        <p className="text-gray-600">
          Add a new job opening with automatic skill extraction
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="card">
        <div className="space-y-6">
          <div>
            <label className="label">
              Job Title <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              {...register('title', { required: 'Title is required' })}
              placeholder="e.g., Senior Python Developer"
              className="input"
              disabled={creating}
            />
            {errors.title && (
              <p className="text-sm text-red-600 mt-1">{errors.title.message}</p>
            )}
          </div>

          <div>
            <label className="label">
              Job Description <span className="text-red-500">*</span>
            </label>
            <textarea
              {...register('description', {
                required: 'Description is required',
                minLength: {
                  value: 10,
                  message: 'Description must be at least 10 characters',
                },
              })}
              placeholder="Describe the role, requirements, and responsibilities..."
              rows={10}
              className="input resize-y"
              disabled={creating}
            />
            {errors.description && (
              <p className="text-sm text-red-600 mt-1">
                {errors.description.message}
              </p>
            )}
            <p className="text-xs text-gray-500 mt-1">
              Include required skills, experience level, and any specific requirements
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="label">Location</label>
              <input
                type="text"
                {...register('location')}
                placeholder="e.g., Hanoi, Vietnam"
                className="input"
                disabled={creating}
              />
            </div>

            <div>
              <label className="label">Remote Policy</label>
              <select
                {...register('remote_policy')}
                className="input"
                disabled={creating}
              >
                <option value="">Select policy</option>
                <option value="on-site">On-site</option>
                <option value="hybrid">Hybrid</option>
                <option value="remote">Remote</option>
              </select>
            </div>
          </div>

          <div>
            <label className="label">Minimum Years of Experience</label>
            <input
              type="number"
              {...register('min_years_experience', {
                valueAsNumber: true,
                min: { value: 0, message: 'Must be 0 or greater' },
              })}
              placeholder="e.g., 3"
              className="input"
              disabled={creating}
              min="0"
            />
            {errors.min_years_experience && (
              <p className="text-sm text-red-600 mt-1">
                {errors.min_years_experience.message}
              </p>
            )}
          </div>

          {error && (
            <div className="flex items-center gap-2 p-4 bg-red-50 border border-red-200 rounded-lg">
              <AlertCircle className="h-5 w-5 text-red-600" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={creating}
              className="btn btn-primary px-6 py-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {creating ? 'Creating Job...' : 'Create Job'}
            </button>
            <button
              type="button"
              onClick={() => navigate('/jobs')}
              className="btn btn-outline px-6 py-2"
              disabled={creating}
            >
              Cancel
            </button>
          </div>

          <div className="mt-6 p-4 bg-blue-50 rounded-lg">
            <h3 className="font-medium text-gray-900 mb-2">
              What happens when you create a job?
            </h3>
            <ul className="text-sm text-gray-600 space-y-1">
              <li>• Job description is normalized for better matching</li>
              <li>• Required skills are automatically extracted</li>
              <li>• Multilingual embeddings are computed (Vietnamese/English)</li>
              <li>• Job is stored and ready for candidate matching</li>
              <li>• You can immediately run matching to find top candidates</li>
            </ul>
          </div>
        </div>
      </form>
    </div>
  )
}
