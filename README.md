# Pomelo

Pomelo is an AI-assisted hiring app built to make hiring feel a little smarter and a lot less noisy.

Candidates can sign up, upload a resume, get matched to roles, swipe on opportunities, and complete a structured interview if there's a match. Recruiters can create roles, monitor interviews live, inject follow-up questions, and compare candidates side by side.

## Why It Matters

Hiring is messy. Candidates send out tons of applications, recruiters sort through piles of low-signal resumes, and good people can get missed.

Pomelo helps fix that with signal compression across the funnel, turning noisy candidate information into a more structured, AI-native hiring workflow that still keeps recruiters in control:

- Better role matching
- Clearer interviews
- Live recruiter visibility
- Stronger decision support at the end

## What We Built

- A React + TypeScript + Vite frontend
- A FastAPI backend with service-based architecture
- Resume upload and AI scoring
- A swipe-based candidate feed
- Live interview flow over WebSocket with voice support TTS transcription
- Recruiter live dashboard over SSE
- Recruiter question injection during interviews
- Candidate comparison support for shortlist decisions

## Technical Highlights

This project shows work across:

**Frontend**
- Frontend architecture with React, TypeScript, Tailwind, and shared design tokens
- Typed client/server data flows
- Product-focused UX for candidate and recruiter flows

**Backend**
- Backend API design with FastAPI, SQLModel, and separated service modules
- LRU-backed prompt and template loading
- AI-assisted resume scoring, grading, summaries, and comparison workflows

**Real-Time**
- Real-time systems using WebSockets and Server-Sent Events
- Real-time communication across candidate interviews and recruiter monitoring
- Low-latency update flows for live interview and dashboard experiences

**AI & Orchestration**
- Vector-based matching and ranking logic
- Concurrent processes for interview flow, grading, follow-up handling, and live updates
- An agentic processing system for orchestrating AI-assisted hiring workflows
- Human-in-the-loop decision support instead of fully automated hiring decisions

## Real-World Impact

The goal of Pomelo is simple: help candidates spend less time applying blindly, help recruiters spend less time sorting weak-fit applications, and make hiring decisions feel more consistent, evidence-backed, and human. The product is AI-native in how it processes resumes, interviews, and comparisons, but it stays human-in-the-loop where it matters most: final judgment.

## Product Flow

### Candidate
1. Sign up
2. Upload resume
3. Get scored and matched
4. Swipe on roles
5. Interview if matched

### Recruiter
1. Create a role
2. Define hidden signals and interview questions
3. Watch interviews live
4. Inject follow-up questions
5. Compare candidates and make a decision

## Future Scaling Plan

As Pomelo grows, the next areas of investment are:

- AI moderation features to flag low-quality or off-topic responses before they reach recruiters
- Multiple rounds of interviewing for higher signal across candidate evaluation
- More advanced AI reasoning for deeper, more nuanced candidate analysis
- Richer feedback for candidates so they can understand how they performed and improve
- A system to track candidate performance over time across applications and interviews
- Cheat detection to flag suspicious behavior during interviews