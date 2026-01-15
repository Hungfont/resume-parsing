# Resume Parsing & Job Matching System - Frontend

Production-grade Next.js 14 application for resume parsing and intelligent job-to-candidate matching with pgvector-powered semantic search and rule-based scoring.

## 🚀 Features

### Core Functionality
- **Resume Upload**: Drag-and-drop interface with skill extraction
- **Job Creation**: Structured forms with automatic skill detection
- **Intelligent Matching**: pgvector semantic search + rule-based evaluation
- **Shortlist Display**: Ranked results with full audit trail
- **Rule Traces**: Transparent scoring with evidence display

### Technical Highlights
- **Next.js 14.1.0**: App Router, React Server Components
- **TypeScript 5.3.3**: Full type safety with strict mode
- **Tailwind CSS 3.4.1**: Utility-first styling with custom theme
- **SWR 2.2.4**: React Hooks for data fetching with caching
- **Native Fetch API**: Modern HTTP client with TypeScript support
- **React Hook Form**: Declarative validation
- **Lucide React**: Modern icon system
- **i18n Support**: Vietnamese/English localization with locale switching

## 📋 Prerequisites

- **Node.js**: 18.17+ or 20+
- **Yarn**: 1.22+ (Package manager)
- **Backend API**: Running on http://localhost:8000

## 🛠️ Installation

### 1. Install Dependencies
```bash
cd fe
yarn install
```

### 2. Configure Environment
```bash
cp .env.local.example .env.local
```

Edit `.env.local`:
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### 3. Run Development Server
```bash
yarn dev
```

Open [http://localhost:3000](http://localhost:3000)

## 📂 Project Structure

```
fe/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── layout.tsx          # Root layout with navigation
│   │   ├── page.tsx            # Dashboard home
│   │   ├── candidates/
│   │   │   ├── page.tsx        # List all candidates
│   │   │   └── upload/
│   │   │       └── page.tsx    # Resume upload
│   │   ├── jobs/
│   │   │   ├── page.tsx        # List all jobs
│   │   │   └── create/
│   │   │       └── page.tsx    # Job creation form
│   │   └── matching/
│   │       └── page.tsx        # Matching & shortlist display
│   ├── components/
│   │   ├── Navigation.tsx      # Top navigation bar
│   │   ├── LocaleProvider.tsx  # i18n provider
│   │   └── LocaleSwitcher.tsx  # Language selector
│   ├── hooks/
│   │   └── useAPI.ts           # SWR hooks for data fetching
│   ├── lib/
│   │   ├── fetcher.ts          # Fetch API wrapper
│   │   ├── utils.ts            # Utility functions
│   │   └── i18n.ts             # Translations (EN/VI)
│   ├── types/
│   │   └── api.ts              # TypeScript interfaces
│   └── styles/
│       └── globals.css         # Global styles + Tailwind
├── public/                     # Static assets
├── package.json
├── tsconfig.json
├── tailwind.config.js
├── next.config.js
└── postcss.config.js
```

## 🎨 Pages & Routes

### Dashboard (`/`)
- System statistics (jobs, candidates, matches)
- Quick action cards
- System features overview

### Candidate Upload (`/candidates/upload`)
- Drag-and-drop resume upload
- Name input field
- Skill extraction display with confidence scores
- Success state with next actions

### Candidates List (`/candidates`)
- All uploaded candidates
- Search by name or skills
- Skill badges sorted by confidence
- Upload count statistics

### Job Creation (`/jobs/create`)
- Structured form with validation
- Fields: title, description, location, remote policy, min years experience
- Skill extraction display
- Success redirect to matching

### Jobs List (`/jobs`)
- All created jobs
- Search by title, description, location, skills
- Quick actions: View, Match
- Job statistics

### Matching & Shortlist (`/matching`)
- Job selection with configuration (topK, topN)
- Run matching pipeline
- Ranked candidate results
- Rule evaluation traces with evidence
- Score breakdown (similarity + rule adjustments)

## 🔌 API Integration

### SWR Hooks

```typescript
import { useCandidates, useJobs, useShortlist } from '@/hooks/useAPI'

// Automatic data fetching with caching
function MyComponent() {
  const { data: candidates, isLoading, error } = useCandidates()
  const { data: jobs } = useJobs()
  const { data: shortlist } = useShortlist(jobId)
  
  // Data is automatically cached and revalidated
  return <div>...</div>
}
```

### Manual API Calls

```typescript
import { postData, uploadFile } from '@/lib/fetcher'
import { useSWRConfig } from 'swr'

function MyComponent() {
  const { mutate } = useSWRConfig()
  
  // Create job
  const createJob = async (data) => {
    const response = await postData('/jobs', data)
    mutate('/jobs') // Revalidate jobs list
    return response
  }
  
  // Upload file
  const uploadResume = async (formData) => {
    const response = await uploadFile('/upload-resume', formData)
    mutate('/candidates') // Revalidate candidates list
    return response
  }
}
```

### Request/Response Types

All API contracts defined in `src/types/api.ts`:
- `Candidate`, `CandidateResponse`
- `Job`, `JobResponse`, `CreateJobRequest`
- `MatchResult`, `RuleTrace`, `Evidence`
- `MatchParams`, `MatchResponse`

## 🎯 Matching Pipeline

### Workflow
1. **Retrieval**: pgvector TopK similarity search (default 500)
2. **Hard Rules**: Filter candidates (must-have requirements)
3. **Soft Rules**: Score adjustments (+/- points)
4. **Ranking**: Sort by final_score DESC
5. **Selection**: TopN shortlist (default 50)
6. **Persistence**: Save with full audit trail

### Configuration
- `top_k`: Initial retrieval count (500-1000)
- `top_n`: Final shortlist size (20-100)
- Rules version: `v1.0.0`
- Embedding model: `all-MiniLM-L6-v2` (384-dim)

## 🧩 Components

### Navigation
- Logo and site title
- Navigation links (Dashboard, Candidates, Jobs, Matching)
- Active route highlighting
- Responsive design

### Cards & Layouts
- Candidate cards with skills
- Job cards with metadata
- Match result cards with rule traces
- Expandable sections

### Forms
- React Hook Form integration
- Inline validation
- Error states
- Success states with data display

## 🎨 Styling

### Tailwind CSS Classes
```css
/* Reusable utilities in globals.css */
.btn                 /* Base button */
.btn-primary         /* Primary action button */
.btn-outline         /* Outlined button */
.card                /* Container card */
.input               /* Form input */
.label               /* Form label */
```

### Color Palette
- Primary: Blue (#2563EB)
- Success: Green (#10B981)
- Warning: Yellow (#F59E0B)
- Error: Red (#EF4444)
- Gray scale: 50-900

## 🧪 Development

### Available Scripts
```bash
yarn dev             # Development server (http://localhost:3000)
yarn build           # Production build
yarn start           # Production server
yarn lint            # ESLint
yarn type-check      # TypeScript checking
```

### Code Quality
- **TypeScript Strict Mode**: Full type checking
- **ESLint**: Code quality rules
- **Prettier**: Code formatting (optional)
- **Path Aliases**: `@/` for src imports

## 🌐 Internationalization (i18n)

### Supported Languages
- ✅ **English** (en)
- ✅ **Vietnamese** (vi)

### Features
- Language switcher in navigation bar
- Locale persistence in localStorage
- Type-safe translation keys
- Context-based translation hook

### Usage
```typescript
import { useTranslation } from '@/lib/i18n'

export function MyComponent() {
  const { t, locale, setLocale } = useTranslation()
  
  return (
    <div>
      <h1>{t.dashboard.title}</h1>
      <button onClick={() => setLocale('vi')}>
        Switch to Vietnamese
      </button>
    </div>
  )
}
```

### Adding Translations
See [I18N_USAGE.md](I18N_USAGE.md) for detailed guide on adding new translations.

## 📦 Build & Deploy

### Production Build
```bash
yarn build
yarn start
```

### Environment Variables
```env
NEXT_PUBLIC_API_BASE_URL=https://api.example.com
```

### Deployment Platforms
- **Vercel**: Zero-config Next.js hosting
- **Netlify**: Static/SSR support
- **AWS Amplify**: Full-stack deployment
- **Docker**: Container with Node.js 18+

## 🚀 Next Steps

### ✅ Completed Features
- ✅ Vietnamese/English i18n with locale switcher
- ✅ Complete matching pipeline with rule traces
- ✅ Candidate and job list pages
- ✅ Dashboard with real-time statistics
- ✅ Resume upload with skill extraction
- ✅ Job creation with form validation

### Future Enhancements
- [ ] Dark mode toggle
- [ ] Advanced search filters
- [ ] Export results to CSV/PDF
- [ ] User authentication
- [ ] Role-based access control
- [ ] Candidate profile pages
- [ ] Job edit/delete
- [ ] Bulk resume upload
- [ ] Analytics dashboard

## 📄 License

MIT License

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

**Built with ❤️ using Next.js, TypeScript, and Tailwind CSS**
