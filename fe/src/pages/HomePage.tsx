import { Link } from 'react-router-dom'
import { Users, Briefcase, GitCompare, TrendingUp, Upload, Plus } from 'lucide-react'
import { useCandidates, useJobs } from '@/hooks/useAPI'

export default function HomePage() {
  const { data: candidates, isLoading: loadingCandidates } = useCandidates()
  const { data: jobs, isLoading: loadingJobs } = useJobs()

  const loading = loadingCandidates || loadingJobs
  const totalCandidates = candidates?.length || 0
  const totalJobs = jobs?.length || 0
  const totalMatches = jobs?.length || 0

  const quickActions = [
    {
      title: 'Upload Resume',
      description: 'Add a new candidate to the system',
      icon: Upload,
      href: '/candidates/upload',
      color: 'bg-blue-500',
    },
    {
      title: 'Create Job',
      description: 'Post a new job opening',
      icon: Plus,
      href: '/jobs/create',
      color: 'bg-green-500',
    },
    {
      title: 'Run Matching',
      description: 'Match jobs to candidates',
      icon: GitCompare,
      href: '/matching',
      color: 'bg-purple-500',
    },
  ]

  const statCards = [
    {
      title: 'Total Candidates',
      value: totalCandidates,
      icon: Users,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      title: 'Active Jobs',
      value: totalJobs,
      icon: Briefcase,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    },
    {
      title: 'Matches Created',
      value: totalMatches,
      icon: TrendingUp,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
    },
  ]

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Resume Matching Dashboard
        </h1>
        <p className="text-gray-600">
          Job → Candidates matching powered by pgvector and ML
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {statCards.map((stat) => {
          const Icon = stat.icon
          return (
            <div key={stat.title} className="card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600 mb-1">
                    {stat.title}
                  </p>
                  <p className="text-3xl font-bold text-gray-900">
                    {loading ? '...' : stat.value}
                  </p>
                </div>
                <div className={`${stat.bgColor} p-3 rounded-lg`}>
                  <Icon className={`h-6 w-6 ${stat.color}`} />
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <div className="mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Quick Actions
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {quickActions.map((action) => {
            const Icon = action.icon
            return (
              <Link
                key={action.title}
                to={action.href}
                className="card hover:shadow-md transition-shadow cursor-pointer"
              >
                <div className="flex items-start gap-4">
                  <div className={`${action.color} p-3 rounded-lg`}>
                    <Icon className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 mb-1">
                      {action.title}
                    </h3>
                    <p className="text-sm text-gray-600">
                      {action.description}
                    </p>
                  </div>
                </div>
              </Link>
            )
          })}
        </div>
      </div>

      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          System Features
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="flex gap-3">
            <div className="text-green-500 mt-1">✓</div>
            <div>
              <h3 className="font-medium text-gray-900 mb-1">
                Multilingual Support
              </h3>
              <p className="text-sm text-gray-600">
                Handles Vietnamese and English resumes/JDs
              </p>
            </div>
          </div>
          <div className="flex gap-3">
            <div className="text-green-500 mt-1">✓</div>
            <div>
              <h3 className="font-medium text-gray-900 mb-1">
                OCR Support
              </h3>
              <p className="text-sm text-gray-600">
                Extracts text from scanned PDFs with Tesseract
              </p>
            </div>
          </div>
          <div className="flex gap-3">
            <div className="text-green-500 mt-1">✓</div>
            <div>
              <h3 className="font-medium text-gray-900 mb-1">
                Skill Extraction
              </h3>
              <p className="text-sm text-gray-600">
                AI-powered skill detection with evidence tracking
              </p>
            </div>
          </div>
          <div className="flex gap-3">
            <div className="text-green-500 mt-1">✓</div>
            <div>
              <h3 className="font-medium text-gray-900 mb-1">
                Rule-Based Scoring
              </h3>
              <p className="text-sm text-gray-600">
                Config-driven rules with full audit trails
              </p>
            </div>
          </div>
          <div className="flex gap-3">
            <div className="text-green-500 mt-1">✓</div>
            <div>
              <h3 className="font-medium text-gray-900 mb-1">
                pgvector Similarity
              </h3>
              <p className="text-sm text-gray-600">
                Fast semantic search with 384-dim embeddings
              </p>
            </div>
          </div>
          <div className="flex gap-3">
            <div className="text-green-500 mt-1">✓</div>
            <div>
              <h3 className="font-medium text-gray-900 mb-1">
                Full Explainability
              </h3>
              <p className="text-sm text-gray-600">
                Every match includes detailed reasoning and evidence
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
