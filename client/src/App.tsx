import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './contexts/auth-context'
import { AppLayout } from './components/app-layout'
import { RequireCandidate, RequireRecruiter } from './components/route-guard'
import { LoginPage } from './pages/login-page'
import { CandidateFeedPage } from './pages/candidate-feed-page'
import { CandidateInterviewPage } from './pages/candidate-interview-page'
import { CandidateMatchesPage } from './pages/candidate-matches-page'
import { CandidateSignupPage } from './pages/candidate-signup-page'
import { RecruiterDashboardPage } from './pages/recruiter-dashboard-page'
import { RecruiterRolesPage } from './pages/recruiter-roles-page'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Standalone — no app shell */}
          <Route path="/login" element={<LoginPage />} />

          {/* App shell routes */}
          <Route element={<AppLayout />}>
            <Route path="/" element={<Navigate to="/login" replace />} />

            {/* Candidate — signup is public so new users can register */}
            <Route path="/candidate/signup" element={<CandidateSignupPage />} />
            <Route
              path="/candidate/feed"
              element={
                <RequireCandidate>
                  <CandidateFeedPage />
                </RequireCandidate>
              }
            />
            <Route
              path="/candidate/matches"
              element={
                <RequireCandidate>
                  <CandidateMatchesPage />
                </RequireCandidate>
              }
            />
            <Route
              path="/candidate/interview/:matchId"
              element={
                <RequireCandidate>
                  <CandidateInterviewPage />
                </RequireCandidate>
              }
            />

            {/* Recruiter */}
            <Route
              path="/recruiter/dashboard"
              element={
                <RequireRecruiter>
                  <RecruiterDashboardPage />
                </RequireRecruiter>
              }
            />
            <Route
              path="/recruiter/roles"
              element={
                <RequireRecruiter>
                  <RecruiterRolesPage />
                </RequireRecruiter>
              }
            />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
