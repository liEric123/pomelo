import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/app-layout'
import { CandidateFeedPage } from './pages/candidate-feed-page'
import { CandidateInterviewPage } from './pages/candidate-interview-page'
import { CandidateMatchesPage } from './pages/candidate-matches-page'
import { CandidateSignupPage } from './pages/candidate-signup-page'
import { RecruiterDashboardPage } from './pages/recruiter-dashboard-page'
import { RecruiterRolesPage } from './pages/recruiter-roles-page'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/candidate/signup" replace />} />
          <Route path="/candidate/signup" element={<CandidateSignupPage />} />
          <Route path="/candidate/feed" element={<CandidateFeedPage />} />
          <Route path="/candidate/matches" element={<CandidateMatchesPage />} />
          <Route
            path="/candidate/interview/:matchId"
            element={<CandidateInterviewPage />}
          />
          <Route
            path="/recruiter/dashboard"
            element={<RecruiterDashboardPage />}
          />
          <Route path="/recruiter/roles" element={<RecruiterRolesPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
