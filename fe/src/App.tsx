import { Routes, Route } from 'react-router-dom'
import { Navigation } from './components/Navigation'
import { LocaleProvider } from './components/LocaleProvider'
import HomePage from './pages/HomePage'
import CandidatesPage from './pages/CandidatesPage'
import CandidateUploadPage from './pages/CandidateUploadPage'
import JobsPage from './pages/JobsPage'
import JobCreatePage from './pages/JobCreatePage'
import JobDetailPage from './pages/JobDetailPage'
import MatchingPage from './pages/MatchingPage'

export default function App() {
  return (
    <LocaleProvider>
      <div className="min-h-screen flex flex-col">
        <Navigation />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/candidates" element={<CandidatesPage />} />
            <Route path="/candidates/upload" element={<CandidateUploadPage />} />
            <Route path="/jobs" element={<JobsPage />} />
            <Route path="/jobs/create" element={<JobCreatePage />} />
            <Route path="/jobs/:id" element={<JobDetailPage />} />
            <Route path="/matching" element={<MatchingPage />} />
          </Routes>
        </main>
        <footer className="border-t border-gray-200 bg-white py-6">
          <div className="container mx-auto px-4 text-center text-sm text-gray-600">
            Resume Matching MVP v0.1.0 | Powered by pgvector + FastAPI + React + Vite
          </div>
        </footer>
      </div>
    </LocaleProvider>
  )
}
