import { useParams } from 'react-router-dom'
import { PlaceholderPage } from '../components/placeholder-page'

export function CandidateInterviewPage() {
  const { matchId } = useParams()

  return (
    <PlaceholderPage
      title="Candidate Interview"
      description={`Placeholder for the live interview experience for match ${matchId ?? 'unknown'}.`}
    />
  )
}
