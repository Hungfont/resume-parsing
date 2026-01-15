import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, X, CheckCircle, AlertCircle } from 'lucide-react'
import { uploadFile } from '@/lib/fetcher'
import { useSWRConfig } from 'swr'
import type { UploadResumeResponse } from '@/types/api'

export default function UploadCandidatePage() {
  const navigate = useNavigate()
  const { mutate } = useSWRConfig()
  const [file, setFile] = useState<File | null>(null)
  const [fullName, setFullName] = useState('')
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<UploadResumeResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0])
      setError(null)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
    },
    maxFiles: 1,
    multiple: false,
  })

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file')
      return
    }

    setUploading(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      if (fullName) {
        formData.append('full_name', fullName)
      }

      const response = await uploadFile<UploadResumeResponse>('/upload-resume', formData)
      setResult(response)
      
      // Revalidate candidates list
      mutate('/candidates')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const handleReset = () => {
    setFile(null)
    setFullName('')
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
                Upload Successful!
              </h1>
              <p className="text-gray-600">Resume processed and stored</p>
            </div>
          </div>

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 p-4 bg-gray-50 rounded-lg">
              <div>
                <p className="text-sm text-gray-600 mb-1">Candidate ID</p>
                <p className="font-medium text-gray-900">{result.candidate_id}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-1">Full Name</p>
                <p className="font-medium text-gray-900">{result.full_name}</p>
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
                  Top Skills Detected
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {result.skills.map((skill, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-3 bg-blue-50 rounded-lg"
                    >
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">
                          {skill.canonical_skill}
                        </p>
                        <p className="text-xs text-gray-600 mt-1 truncate">
                          {skill.evidence}
                        </p>
                      </div>
                      <div className="ml-3 px-2 py-1 bg-blue-100 rounded text-sm font-medium text-blue-700">
                        {(skill.confidence * 100).toFixed(0)}%
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex gap-3 pt-4">
              <button
                onClick={handleReset}
                className="btn btn-primary px-6 py-2"
              >
                Upload Another Resume
              </button>
              <button
                onClick={() => navigate('/candidates')}
                className="btn btn-outline px-6 py-2"
              >
                View All Candidates
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
          Upload Resume
        </h1>
        <p className="text-gray-600">
          Upload a candidate resume in PDF, CSV, or Excel format
        </p>
      </div>

      <div className="card">
        <div className="space-y-6">
          <div>
            <label className="label">
              Full Name (Optional)
            </label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="e.g., John Doe"
              className="input"
              disabled={uploading}
            />
            <p className="text-xs text-gray-500 mt-1">
              Leave empty to auto-extract from resume
            </p>
          </div>

          <div>
            <label className="label">
              Resume File
            </label>
            <div
              {...getRootProps()}
              className={`
                border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
                transition-colors
                ${isDragActive
                  ? 'border-primary-500 bg-primary-50'
                  : 'border-gray-300 hover:border-primary-400'
                }
                ${uploading ? 'opacity-50 cursor-not-allowed' : ''}
              `}
            >
              <input {...getInputProps()} disabled={uploading} />
              <Upload className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              {file ? (
                <div className="flex items-center justify-center gap-3">
                  <FileText className="h-5 w-5 text-primary-600" />
                  <span className="font-medium text-gray-900">{file.name}</span>
                  {!uploading && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        setFile(null)
                      }}
                      className="p-1 hover:bg-gray-100 rounded"
                    >
                      <X className="h-4 w-4 text-gray-500" />
                    </button>
                  )}
                </div>
              ) : (
                <>
                  <p className="text-gray-700 font-medium mb-1">
                    {isDragActive
                      ? 'Drop the file here'
                      : 'Drag & drop resume file here'}
                  </p>
                  <p className="text-sm text-gray-500">
                    or click to browse
                  </p>
                  <p className="text-xs text-gray-400 mt-2">
                    Supported: PDF, CSV, Excel
                  </p>
                </>
              )}
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2 p-4 bg-red-50 border border-red-200 rounded-lg">
              <AlertCircle className="h-5 w-5 text-red-600" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={handleUpload}
              disabled={!file || uploading}
              className="btn btn-primary px-6 py-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {uploading ? 'Processing...' : 'Upload Resume'}
            </button>
            <button
              onClick={() => navigate('/candidates')}
              className="btn btn-outline px-6 py-2"
              disabled={uploading}
            >
              Cancel
            </button>
          </div>

          <div className="mt-6 p-4 bg-blue-50 rounded-lg">
            <h3 className="font-medium text-gray-900 mb-2">
              What happens after upload?
            </h3>
            <ul className="text-sm text-gray-600 space-y-1">
              <li>• Resume text is extracted (with OCR for scanned PDFs)</li>
              <li>• Skills are automatically detected and categorized</li>
              <li>• Multilingual embeddings are computed (384-dim)</li>
              <li>• Candidate profile is stored in database</li>
              <li>• Ready for job matching immediately</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
