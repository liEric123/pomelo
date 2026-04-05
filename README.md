# Pomelo

Pomelo is an AI-assisted hiring app built to make hiring feel a little smarter and a lot less noisy.

Candidates can sign up, upload a resume, get matched to roles, swipe on opportunities, and complete a structured interview if there's a match. Recruiters can create roles, monitor interviews live, inject follow-up questions, and compare candidates side by side.

## Why It Matters

Hiring is messy. Candidates send out tons of applications, recruiters sort through piles of low-signal resumes, and good people can get missed.

Pomelo helps fix that by making the process more structured:
- better role matching
- clearer interviews
- live recruiter visibility
- stronger decision support at the end

## What We Built

- a React + TypeScript + Vite frontend
- a FastAPI backend with service-based architecture
- resume upload and AI scoring
- a swipe-based candidate feed
- live interview flow over WebSocket
- recruiter live dashboard over SSE
- recruiter question injection during interviews
- candidate comparison support for shortlist decisions

## Technical Highlights

This project shows work across:
- frontend architecture with React, TypeScript, Tailwind, and shared design tokens
- backend API design with FastAPI, SQLModel, and separated service modules
- real-time systems using WebSockets and Server-Sent Events
- real-time communication across candidate interviews and recruiter monitoring
- vector-based matching and ranking logic
- LRU-backed prompt and template loading
- concurrent processes for interview flow, grading, follow-up handling, and live updates
- an agentic processing system for orchestrating AI-assisted hiring workflows
- typed client/server data flows
- AI-assisted resume scoring, grading, summaries, and comparison workflows
- product-focused UX for candidate and recruiter flows

## Real-World Impact

The goal of Pomelo is simple: help candidates spend less time applying blindly, help recruiters spend less time sorting weak-fit applications, and make hiring decisions feel more consistent, evidence-backed, and human.

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

## Architecture Notes

Pomelo follows a clean service-oriented structure:
- thin routes
- focused backend services
- a central `HiringCoordinator`
- concurrent processes supporting live interview progression and recruiter-side event delivery
- typed real-time event payloads
- AI responsibilities split by domain instead of packed into one giant file

## In Short

Pomelo is a hiring platform that tries to turn a chaotic process into a clearer one, using AI as a helper, not a replacement for human judgment.
