from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from sqlalchemy.engine import make_url
from sqlmodel import Session, select

from database import DATABASE_URL, create_db_and_tables, engine
from models import (
    Candidate,
    Company,
    InterviewMessage,
    Match,
    MatchStatus,
    MessageRole,
    Role,
    Swipe,
    SwipeDirection,
)
from services.resume_service import SKILL_VOCABULARY

DEMO_MARKER = "[Pomelo demo seed]"
DEMO_EMAIL_DOMAIN = "@demo.pomelo.test"
UTC = timezone.utc
BASE_TIME = datetime(2026, 4, 2, 14, 0, tzinfo=UTC)

COMPANIES = [
    {
        "alias": "openai",
        "name": "OpenAI",
        "website": "https://openai.com",
        "description": (
            "Research and deployment company focused on general-purpose AI systems "
            "and developer platforms. Public-facing demo data inspired by well-known "
            "company themes only; not a live hiring post. "
            f"{DEMO_MARKER}"
        ),
        "created_at": BASE_TIME - timedelta(days=28),
        "roles": [
            {
                "alias": "openai_applied_ai",
                "title": "Applied AI Engineer",
                "description": (
                    "Build product-facing AI workflows that connect model behavior, "
                    "evaluation, and user experience. This demo role is inspired by "
                    "public discussions around applied AI product engineering and does "
                    "not represent a live posting. "
                    f"{DEMO_MARKER}"
                ),
                "location": "San Francisco, CA",
                "is_remote": False,
                "min_score": 0.72,
                "max_score": 1.0,
                "max_swipes_per_day": 30,
                "keywords": [
                    "Python",
                    "TypeScript",
                    "FastAPI",
                    "React",
                    "PyTorch",
                    "REST API",
                    "System Design",
                    "Machine Learning",
                ],
                "questions": [
                    "Tell me about an AI-powered feature you shipped end to end and how you measured quality after launch.",
                    "How do you translate a vague product request into a concrete evaluation plan for an LLM-backed workflow?",
                    "Describe a time you improved latency, reliability, or cost for a model-enabled service in production.",
                    "When would you choose prompting, retrieval, or fine-tuning for a product use case, and what tradeoffs matter most?",
                    "How would you instrument a new AI feature so product, engineering, and safety teams can all trust the rollout?",
                    "Describe a production issue where model behavior surprised users and how you handled the incident.",
                    "Explain in plain English how vector similarity search fits into a product experience.",
                    "Walk through pseudocode for a service that ranks candidate profiles against recruiter-defined keywords.",
                ],
                "created_at": BASE_TIME - timedelta(days=27, hours=4),
            },
            {
                "alias": "openai_inference_platform",
                "title": "Inference Platform Engineer",
                "description": (
                    "Work on the systems that support reliable, observable, and efficient "
                    "model serving. This demo role is a plausible platform theme based on "
                    "public infrastructure work and is not a live posting. "
                    f"{DEMO_MARKER}"
                ),
                "location": "San Francisco, CA",
                "is_remote": False,
                "min_score": 0.68,
                "max_score": 1.0,
                "max_swipes_per_day": 28,
                "keywords": [
                    "Python",
                    "Go",
                    "Kubernetes",
                    "Docker",
                    "AWS",
                    "Linux",
                    "CI/CD",
                    "System Design",
                ],
                "questions": [
                    "Describe a platform reliability problem you owned and the metrics you used to prove it improved.",
                    "How do you design safe rollout mechanics for a serving system with strict latency targets?",
                    "Tell me about a time you reduced noisy alerts or improved observability for a distributed service.",
                    "What failure modes do you look for first in a high-throughput model inference pipeline?",
                    "How would you balance developer velocity with reliability when multiple product teams depend on one platform?",
                    "Describe a production incident where capacity planning or autoscaling assumptions were wrong.",
                    "Explain in plain English how Kubernetes helps with resilient service deployment.",
                    "Walk through pseudocode for a queue-based worker that retries failed inference jobs without duplicating work.",
                ],
                "created_at": BASE_TIME - timedelta(days=26, hours=18),
            },
        ],
    },
    {
        "alias": "goldman",
        "name": "Goldman Sachs",
        "website": "https://www.goldmansachs.com",
        "description": (
            "Global financial institution with widely known work across investment banking, "
            "markets, and digital consumer experiences. Public-facing demo data only; not "
            "a live hiring post. "
            f"{DEMO_MARKER}"
        ),
        "created_at": BASE_TIME - timedelta(days=24),
        "roles": [
            {
                "alias": "goldman_digital_banking",
                "title": "Software Engineer, Digital Banking Platform",
                "description": (
                    "Build customer-facing software and backend services for modern digital "
                    "banking experiences. This demo role uses a plausible public-facing theme "
                    "and does not represent a live posting. "
                    f"{DEMO_MARKER}"
                ),
                "location": "New York, NY",
                "is_remote": False,
                "min_score": 0.58,
                "max_score": 0.95,
                "max_swipes_per_day": 32,
                "keywords": [
                    "Java",
                    "TypeScript",
                    "React",
                    "SQL",
                    "PostgreSQL",
                    "AWS",
                    "Microservices",
                    "Security",
                ],
                "questions": [
                    "Tell me about a customer-facing financial or transactional workflow you helped build and how you protected reliability.",
                    "How do you approach API and data model design for systems with strict correctness requirements?",
                    "Describe a time you balanced shipping product work with tightening security or compliance controls.",
                    "How have you handled operational issues in a service that other teams depended on heavily?",
                    "Describe a project where you had to coordinate frontend and backend changes under a tight deadline.",
                    "What tradeoffs do you make when decomposing a monolith into services in a regulated environment?",
                    "Explain in plain English what idempotency means and why it matters for money movement or account actions.",
                    "Walk through pseudocode for preventing duplicate submission of a sensitive account update request.",
                ],
                "created_at": BASE_TIME - timedelta(days=23, hours=8),
            },
            {
                "alias": "goldman_risk_data",
                "title": "Data Engineer, Risk Analytics",
                "description": (
                    "Build data pipelines and analytics foundations that support risk and "
                    "reporting workflows. This demo role is a plausible theme based on "
                    "public-facing financial data engineering work and is not a live posting. "
                    f"{DEMO_MARKER}"
                ),
                "location": "Dallas, TX",
                "is_remote": False,
                "min_score": 0.6,
                "max_score": 0.96,
                "max_swipes_per_day": 26,
                "keywords": [
                    "Python",
                    "SQL",
                    "PostgreSQL",
                    "Spark",
                    "Data Engineering",
                    "AWS",
                    "Security",
                    "Git",
                ],
                "questions": [
                    "Describe a data pipeline you built where lineage, reconciliation, or auditability mattered.",
                    "How do you design datasets for both analytical flexibility and operational trust?",
                    "Tell me about a time late or incorrect upstream data created business risk and how you responded.",
                    "What testing strategy do you use for complex ETL or streaming jobs?",
                    "How do you keep data platform changes understandable for analysts, engineers, and control partners?",
                    "Describe a time you improved the cost or runtime of a large-scale batch workflow.",
                    "Explain in plain English how partitioning can improve performance in a warehouse or lakehouse pipeline.",
                    "Walk through pseudocode for validating that a daily position feed is complete before publishing it downstream.",
                ],
                "created_at": BASE_TIME - timedelta(days=22, hours=14),
            },
        ],
    },
    {
        "alias": "uhg",
        "name": "UnitedHealth Group",
        "website": "https://www.unitedhealthgroup.com",
        "description": (
            "Healthcare and benefits organization known publicly for large-scale digital, "
            "analytics, and care operations. Public-facing demo data only; not a live hiring post. "
            f"{DEMO_MARKER}"
        ),
        "created_at": BASE_TIME - timedelta(days=20),
        "roles": [
            {
                "alias": "uhg_data_platform",
                "title": "Senior Data Platform Engineer",
                "description": (
                    "Build pipelines and data services that support healthcare operations, "
                    "analytics, and internal decision support. This demo role reflects a "
                    "plausible public theme and is not a live posting. "
                    f"{DEMO_MARKER}"
                ),
                "location": "Eden Prairie, MN",
                "is_remote": True,
                "min_score": 0.62,
                "max_score": 0.95,
                "max_swipes_per_day": 24,
                "keywords": [
                    "Python",
                    "SQL",
                    "Spark",
                    "PostgreSQL",
                    "Data Engineering",
                    "AWS",
                    "CI/CD",
                    "Security",
                ],
                "questions": [
                    "Describe a healthcare, operations, or regulated-data pipeline you built and how you protected data quality.",
                    "How do you make data platform work useful to both engineering teams and business stakeholders?",
                    "Tell me about a time you had to debug a hard-to-reproduce data discrepancy across environments.",
                    "How do you design access controls and auditability for sensitive datasets?",
                    "Describe an instance where you improved the reliability of an ingestion or transformation workflow.",
                    "How would you prioritize schema evolution work when several downstream teams depend on the same dataset?",
                    "Explain in plain English why slowly changing dimensions matter for longitudinal reporting.",
                    "Walk through pseudocode for deduplicating member events before loading them into an analytics table.",
                ],
                "created_at": BASE_TIME - timedelta(days=19, hours=10),
            },
            {
                "alias": "uhg_member_experience",
                "title": "Software Engineer, Digital Member Experience",
                "description": (
                    "Build web experiences and APIs that help members navigate benefits and "
                    "care workflows. This demo role is a plausible public-facing scenario "
                    "and does not represent a live posting. "
                    f"{DEMO_MARKER}"
                ),
                "location": "Remote",
                "is_remote": True,
                "min_score": 0.48,
                "max_score": 0.88,
                "max_swipes_per_day": 25,
                "keywords": [
                    "TypeScript",
                    "React",
                    "Node.js",
                    "REST API",
                    "AWS",
                    "GraphQL",
                    "Security",
                    "System Design",
                ],
                "questions": [
                    "Tell me about a user-facing workflow you improved where clarity and trust mattered as much as feature velocity.",
                    "How do you coordinate frontend and backend changes when a member-facing release touches several systems?",
                    "Describe a time accessibility or usability feedback changed your implementation approach.",
                    "How do you protect personally sensitive data in a product experience without making the UX feel brittle?",
                    "Describe a production issue in a web application that required fast debugging across the stack.",
                    "What signals do you watch after releasing a new member-facing flow?",
                    "Explain in plain English when GraphQL is helpful and when a REST API may be simpler.",
                    "Walk through pseudocode for loading a member dashboard with partial fallbacks when one downstream service is unavailable.",
                ],
                "created_at": BASE_TIME - timedelta(days=18, hours=7),
            },
        ],
    },
]

CANDIDATES = [
    {
        "alias": "mira_patel",
        "name": "Mira Patel",
        "email": "mira.patel@demo.pomelo.test",
        "summary": (
            "Applied AI engineer with experience shipping evaluation-driven assistant "
            "features, backend APIs, and model-serving improvements across startup and "
            "platform environments."
        ),
        "top_skills": ["Python", "PyTorch", "FastAPI", "TypeScript", "Machine Learning"],
        "resume_score": 0.92,
        "resume_text": (
            "Mira Patel is a software engineer focused on applied AI products. "
            "She recently led delivery of a retrieval-augmented assistant for a B2B "
            "workflow tool, owned Python and FastAPI services, wrote TypeScript feature "
            "surfaces, and built evaluation dashboards for groundedness and latency. "
            "Earlier she worked on ML infrastructure, PyTorch experimentation, and prompt "
            "quality tooling. She enjoys cross-functional work with product, design, and "
            "safety partners."
        ),
        "embedding_skills": {
            "Python": 0.98,
            "TypeScript": 0.82,
            "FastAPI": 0.9,
            "React": 0.74,
            "PyTorch": 0.9,
            "REST API": 0.86,
            "System Design": 0.77,
            "Machine Learning": 0.94,
            "PostgreSQL": 0.55,
            "AWS": 0.5,
            "Git": 0.8,
        },
        "created_at": BASE_TIME - timedelta(days=16, hours=1),
    },
    {
        "alias": "ethan_brooks",
        "name": "Ethan Brooks",
        "email": "ethan.brooks@demo.pomelo.test",
        "summary": (
            "Backend and product engineer with digital banking and payments experience, "
            "strong Java services fundamentals, and a track record of leading cross-stack releases."
        ),
        "top_skills": ["Java", "TypeScript", "React", "PostgreSQL", "AWS"],
        "resume_score": 0.86,
        "resume_text": (
            "Ethan Brooks builds customer-facing financial software. He has worked on "
            "Java microservices, PostgreSQL-backed APIs, and React applications for account "
            "management and onboarding workflows. He has handled incident response, security "
            "reviews, and design sessions for service decomposition in regulated environments."
        ),
        "embedding_skills": {
            "Java": 0.94,
            "TypeScript": 0.8,
            "React": 0.76,
            "SQL": 0.84,
            "PostgreSQL": 0.83,
            "AWS": 0.78,
            "Microservices": 0.82,
            "Security": 0.73,
            "REST API": 0.86,
            "Git": 0.77,
        },
        "created_at": BASE_TIME - timedelta(days=15, hours=7),
    },
    {
        "alias": "sofia_ramirez",
        "name": "Sofia Ramirez",
        "email": "sofia.ramirez@demo.pomelo.test",
        "summary": (
            "Healthcare data platform engineer with strong batch-processing, warehouse, "
            "and data quality experience across sensitive operational datasets."
        ),
        "top_skills": ["Python", "SQL", "Spark", "Data Engineering", "AWS"],
        "resume_score": 0.88,
        "resume_text": (
            "Sofia Ramirez has spent the last several years building healthcare analytics "
            "and operations pipelines. She owns Python and Spark jobs, writes SQL for "
            "warehouse modeling, automates CI/CD for data releases, and works closely with "
            "analytics and operations teams on trusted datasets. She is especially strong "
            "at debugging data quality issues and documenting lineage."
        ),
        "embedding_skills": {
            "Python": 0.9,
            "SQL": 0.94,
            "Spark": 0.88,
            "PostgreSQL": 0.7,
            "Data Engineering": 0.95,
            "AWS": 0.73,
            "CI/CD": 0.68,
            "Security": 0.66,
            "Pandas": 0.72,
            "Git": 0.75,
        },
        "created_at": BASE_TIME - timedelta(days=14, hours=3),
    },
    {
        "alias": "jordan_lee",
        "name": "Jordan Lee",
        "email": "jordan.lee@demo.pomelo.test",
        "summary": (
            "Product-minded full-stack engineer with strong React, Node.js, and GraphQL "
            "experience shipping user-facing workflows for operational teams."
        ),
        "top_skills": ["TypeScript", "React", "Node.js", "GraphQL", "System Design"],
        "resume_score": 0.78,
        "resume_text": (
            "Jordan Lee builds web products that connect design, product, and operations. "
            "He has shipped React and TypeScript applications, Node.js services, GraphQL "
            "APIs, and analytics instrumentation for complex user journeys. He often owns "
            "cross-functional releases and is comfortable debugging issues from browser to database."
        ),
        "embedding_skills": {
            "TypeScript": 0.92,
            "React": 0.9,
            "Node.js": 0.82,
            "GraphQL": 0.8,
            "REST API": 0.7,
            "System Design": 0.72,
            "AWS": 0.55,
            "Security": 0.5,
            "HTML": 0.74,
            "CSS": 0.72,
        },
        "created_at": BASE_TIME - timedelta(days=13, hours=9),
    },
    {
        "alias": "priya_nair",
        "name": "Priya Nair",
        "email": "priya.nair@demo.pomelo.test",
        "summary": (
            "Data engineer with financial reporting and controls experience, strong SQL "
            "and Spark fundamentals, and a careful approach to lineage and reconciliation."
        ),
        "top_skills": ["Python", "SQL", "PostgreSQL", "Spark", "Security"],
        "resume_score": 0.74,
        "resume_text": (
            "Priya Nair works on risk and reporting data problems. She has built Python "
            "and Spark transformations, tuned PostgreSQL workloads, partnered with finance "
            "stakeholders on reconciliations, and improved data validation checks for daily "
            "reporting pipelines. She is known for clear documentation and thoughtful controls."
        ),
        "embedding_skills": {
            "Python": 0.78,
            "SQL": 0.9,
            "PostgreSQL": 0.83,
            "Spark": 0.8,
            "Data Engineering": 0.74,
            "AWS": 0.58,
            "Security": 0.71,
            "Git": 0.72,
            "Pandas": 0.65,
        },
        "created_at": BASE_TIME - timedelta(days=12, hours=11),
    },
    {
        "alias": "caleb_wright",
        "name": "Caleb Wright",
        "email": "caleb.wright@demo.pomelo.test",
        "summary": (
            "Frontend-leaning software engineer who has shipped React and Node.js features "
            "for consumer experiences and internal support tooling."
        ),
        "top_skills": ["TypeScript", "React", "Node.js", "CSS", "REST API"],
        "resume_score": 0.68,
        "resume_text": (
            "Caleb Wright focuses on polished web experiences. He has shipped TypeScript "
            "and React interfaces, integrated REST APIs, contributed Node.js endpoints, "
            "and partnered with design on experimentation and usability improvements. "
            "He is strongest in frontend execution and cross-team communication."
        ),
        "embedding_skills": {
            "TypeScript": 0.84,
            "React": 0.88,
            "Node.js": 0.68,
            "CSS": 0.8,
            "REST API": 0.7,
            "HTML": 0.75,
            "GraphQL": 0.52,
            "Git": 0.7,
        },
        "created_at": BASE_TIME - timedelta(days=11, hours=5),
    },
    {
        "alias": "hannah_chen",
        "name": "Hannah Chen",
        "email": "hannah.chen@demo.pomelo.test",
        "summary": (
            "Platform engineer with strong Kubernetes, CI/CD, and Linux operations "
            "experience supporting high-throughput internal services."
        ),
        "top_skills": ["Go", "Kubernetes", "Docker", "AWS", "CI/CD"],
        "resume_score": 0.57,
        "resume_text": (
            "Hannah Chen works on service platform tooling and deployment reliability. "
            "She has managed Kubernetes clusters, built Go helpers for internal developer "
            "workflows, improved CI/CD speed, and reduced noisy infrastructure alerts. "
            "She is comfortable with Linux, containers, and operational debugging."
        ),
        "embedding_skills": {
            "Go": 0.76,
            "Kubernetes": 0.88,
            "Docker": 0.85,
            "AWS": 0.74,
            "Linux": 0.82,
            "CI/CD": 0.84,
            "System Design": 0.48,
            "Git": 0.68,
        },
        "created_at": BASE_TIME - timedelta(days=10, hours=13),
    },
    {
        "alias": "leo_martinez",
        "name": "Leo Martinez",
        "email": "leo.martinez@demo.pomelo.test",
        "summary": (
            "Early-career engineer with internship experience in QA automation and basic "
            "web development, showing promise but still building depth."
        ),
        "top_skills": ["Python", "HTML", "CSS", "Git"],
        "resume_score": 0.35,
        "resume_text": (
            "Leo Martinez recently completed a software engineering internship where he "
            "helped with QA automation scripts, internal dashboard tweaks, and bug triage. "
            "He has classroom and internship experience with Python, basic HTML and CSS, "
            "and version control, and is looking for a role with strong mentorship."
        ),
        "embedding_skills": {
            "Python": 0.42,
            "HTML": 0.45,
            "CSS": 0.4,
            "Git": 0.38,
        },
        "created_at": BASE_TIME - timedelta(days=9, hours=4),
    },
]

SWIPES = [
    {
        "candidate_alias": "mira_patel",
        "role_alias": "openai_applied_ai",
        "candidate_direction": SwipeDirection.like,
        "candidate_swiped_at": BASE_TIME - timedelta(days=3, hours=6),
        "recruiter_direction": SwipeDirection.like,
        "recruiter_swiped_at": BASE_TIME - timedelta(days=3, hours=2),
        "keyword_score": 0.95,
        "keyword_reasoning": (
            "Direct applied AI product experience, strong evaluation mindset, and clear "
            "alignment with Python plus model-serving workflows."
        ),
        "keyword_approved": True,
        "created_at": BASE_TIME - timedelta(days=3, hours=6),
    },
    {
        "candidate_alias": "ethan_brooks",
        "role_alias": "goldman_digital_banking",
        "candidate_direction": SwipeDirection.like,
        "candidate_swiped_at": BASE_TIME - timedelta(days=4, hours=7),
        "recruiter_direction": SwipeDirection.like,
        "recruiter_swiped_at": BASE_TIME - timedelta(days=4, hours=1),
        "keyword_score": 0.88,
        "keyword_reasoning": (
            "Strong overlap with customer-facing financial systems, Java services, and "
            "security-minded delivery in regulated environments."
        ),
        "keyword_approved": True,
        "created_at": BASE_TIME - timedelta(days=4, hours=7),
    },
    {
        "candidate_alias": "sofia_ramirez",
        "role_alias": "uhg_data_platform",
        "candidate_direction": SwipeDirection.like,
        "candidate_swiped_at": BASE_TIME - timedelta(days=6, hours=3),
        "recruiter_direction": SwipeDirection.like,
        "recruiter_swiped_at": BASE_TIME - timedelta(days=6, hours=1),
        "keyword_score": 0.91,
        "keyword_reasoning": (
            "Excellent fit for large-scale healthcare-style data engineering with strong "
            "Spark, SQL, lineage, and reliability signals."
        ),
        "keyword_approved": True,
        "created_at": BASE_TIME - timedelta(days=6, hours=3),
    },
    {
        "candidate_alias": "priya_nair",
        "role_alias": "goldman_risk_data",
        "candidate_direction": SwipeDirection.like,
        "candidate_swiped_at": BASE_TIME - timedelta(days=2, hours=12),
        "recruiter_direction": None,
        "recruiter_swiped_at": None,
        "keyword_score": 0.84,
        "keyword_reasoning": (
            "Relevant risk-data background with solid SQL, Spark, and controls-oriented "
            "thinking. Worth recruiter review."
        ),
        "keyword_approved": True,
        "created_at": BASE_TIME - timedelta(days=2, hours=12),
    },
    {
        "candidate_alias": "hannah_chen",
        "role_alias": "openai_inference_platform",
        "candidate_direction": SwipeDirection.like,
        "candidate_swiped_at": BASE_TIME - timedelta(days=2, hours=5),
        "recruiter_direction": None,
        "recruiter_swiped_at": None,
        "keyword_score": 0.79,
        "keyword_reasoning": (
            "Strong operational platform signals with Kubernetes, CI/CD, and Linux; less "
            "model-specific depth, but the platform fit is plausible."
        ),
        "keyword_approved": True,
        "created_at": BASE_TIME - timedelta(days=2, hours=5),
    },
    {
        "candidate_alias": "jordan_lee",
        "role_alias": "uhg_member_experience",
        "candidate_direction": SwipeDirection.like,
        "candidate_swiped_at": BASE_TIME - timedelta(days=1, hours=16),
        "recruiter_direction": None,
        "recruiter_swiped_at": None,
        "keyword_score": None,
        "keyword_reasoning": None,
        "keyword_approved": None,
        "created_at": BASE_TIME - timedelta(days=1, hours=16),
    },
    {
        "candidate_alias": "caleb_wright",
        "role_alias": "uhg_member_experience",
        "candidate_direction": SwipeDirection.like,
        "candidate_swiped_at": BASE_TIME - timedelta(days=2, hours=9),
        "recruiter_direction": SwipeDirection.pass_,
        "recruiter_swiped_at": BASE_TIME - timedelta(days=2, hours=2),
        "keyword_score": 0.62,
        "keyword_reasoning": (
            "Frontend execution is solid, but the role needs more backend API ownership "
            "and stronger security depth."
        ),
        "keyword_approved": False,
        "created_at": BASE_TIME - timedelta(days=2, hours=9),
    },
    {
        "candidate_alias": "leo_martinez",
        "role_alias": "goldman_digital_banking",
        "candidate_direction": SwipeDirection.like,
        "candidate_swiped_at": BASE_TIME - timedelta(days=1, hours=20),
        "recruiter_direction": SwipeDirection.pass_,
        "recruiter_swiped_at": BASE_TIME - timedelta(days=1, hours=18),
        "keyword_score": 0.31,
        "keyword_reasoning": (
            "Promising fundamentals, but experience is still too early for a banking platform role with production ownership."
        ),
        "keyword_approved": False,
        "created_at": BASE_TIME - timedelta(days=1, hours=20),
    },
]

MATCHES = [
    {
        "candidate_alias": "ethan_brooks",
        "role_alias": "goldman_digital_banking",
        "status": MatchStatus.pending,
        "matched_at": BASE_TIME - timedelta(days=4),
        "completed_at": None,
        "final_score": None,
        "recommendation": None,
        "interview_summary": None,
    },
    {
        "candidate_alias": "mira_patel",
        "role_alias": "openai_applied_ai",
        "status": MatchStatus.interviewing,
        "matched_at": BASE_TIME - timedelta(days=3),
        "completed_at": None,
        "final_score": None,
        "recommendation": None,
        "interview_summary": None,
    },
    {
        "candidate_alias": "sofia_ramirez",
        "role_alias": "uhg_data_platform",
        "status": MatchStatus.completed,
        "matched_at": BASE_TIME - timedelta(days=6),
        "completed_at": BASE_TIME - timedelta(days=5, hours=20),
        "final_score": 0.87,
        "recommendation": "strong yes",
        "interview_summary": json.dumps(
            {
                "behavioral_score": 0.89,
                "communication_score": 0.84,
                "concerns": [
                    "Could be sharper on rough-order capacity planning assumptions for fast-changing data volume."
                ],
                "confidence": 0.86,
                "flags_summary": [],
                "interviewer_notes": {
                    "do_not_ask_again": [
                        "Data quality ownership",
                        "Cross-functional stakeholder communication",
                    ],
                    "suggested_opener": (
                        "Start by asking how she would phase observability upgrades for a new healthcare data domain."
                    ),
                    "topics_to_probe": [
                        "Real-time pipeline design",
                        "Cost controls at larger scale",
                    ],
                },
                "one_liner": (
                    "Strong healthcare data platform operator with trustworthy execution and clear communication."
                ),
                "scores_weighted": 0.87,
                "strengths": [
                    "Owns data quality and lineage end to end",
                    "Communicates tradeoffs clearly to technical and non-technical partners",
                    "Strong Spark and SQL foundation for regulated data workflows",
                ],
                "technical_score": 0.85,
                "verdict": "ADVANCE",
            },
            sort_keys=True,
        ),
    },
]

INTERVIEW_MESSAGES = [
    {
        "match_key": ("mira_patel", "openai_applied_ai"),
        "role": MessageRole.question,
        "content": COMPANIES[0]["roles"][0]["questions"][0],
        "question_index": 0,
        "recruiter_injected": False,
        "created_at": BASE_TIME - timedelta(days=2, hours=23, minutes=40),
    },
    {
        "match_key": ("mira_patel", "openai_applied_ai"),
        "role": MessageRole.answer,
        "content": (
            "At my last startup I shipped a support copilot that summarized account context "
            "and drafted next-step recommendations. I owned the FastAPI service, built offline "
            "evals for citation quality, and set alert thresholds when groundedness dropped after deployment."
        ),
        "question_index": 0,
        "score": 0.91,
        "score_label": "strong",
        "flags": [],
        "grade_reasoning": "Specific ownership, clear eval strategy, and strong production follow-through.",
        "recruiter_injected": False,
        "created_at": BASE_TIME - timedelta(days=2, hours=23, minutes=34),
    },
    {
        "match_key": ("mira_patel", "openai_applied_ai"),
        "role": MessageRole.question,
        "content": COMPANIES[0]["roles"][0]["questions"][1],
        "question_index": 1,
        "recruiter_injected": False,
        "created_at": BASE_TIME - timedelta(days=2, hours=23, minutes=31),
    },
    {
        "match_key": ("mira_patel", "openai_applied_ai"),
        "role": MessageRole.answer,
        "content": (
            "I start by defining the user promise, then I create a small golden set and "
            "failure taxonomy before discussing architecture. That lets product and engineering "
            "agree on what 'good' looks like before we optimize prompts or retrieval."
        ),
        "question_index": 1,
        "score": 0.87,
        "score_label": "strong",
        "flags": [],
        "grade_reasoning": "Grounded framework with good prioritization of evals and stakeholder alignment.",
        "recruiter_injected": False,
        "created_at": BASE_TIME - timedelta(days=2, hours=23, minutes=25),
    },
    {
        "match_key": ("mira_patel", "openai_applied_ai"),
        "role": MessageRole.follow_up,
        "content": "What changed in your eval plan once real user traffic exposed new edge cases?",
        "question_index": None,
        "recruiter_injected": True,
        "created_at": BASE_TIME - timedelta(days=2, hours=23, minutes=22),
    },
    {
        "match_key": ("mira_patel", "openai_applied_ai"),
        "role": MessageRole.answer,
        "content": (
            "We added a slice for low-context tickets and reweighted the eval set toward "
            "cases where the retriever returned near-duplicates. We also introduced manual "
            "review on a small sample each week so drift did not hide behind aggregate scores."
        ),
        "question_index": None,
        "score": 0.84,
        "score_label": "strong",
        "flags": [],
        "grade_reasoning": "Good evidence of iterative thinking once production traffic changed the problem shape.",
        "recruiter_injected": True,
        "created_at": BASE_TIME - timedelta(days=2, hours=23, minutes=17),
    },
    {
        "match_key": ("mira_patel", "openai_applied_ai"),
        "role": MessageRole.question,
        "content": COMPANIES[0]["roles"][0]["questions"][2],
        "question_index": 2,
        "recruiter_injected": False,
        "created_at": BASE_TIME - timedelta(days=2, hours=23, minutes=12),
    },
    {
        "match_key": ("mira_patel", "openai_applied_ai"),
        "role": MessageRole.answer,
        "content": (
            "I reduced p95 latency by splitting retrieval from generation, caching "
            "stable account metadata, and adding request budgets per downstream dependency. "
            "The change cut user-visible latency by about a third without hurting answer quality."
        ),
        "question_index": 2,
        "score": 0.89,
        "score_label": "strong",
        "flags": [],
        "grade_reasoning": "Strong technical ownership with concrete latency improvements and sensible tradeoffs.",
        "recruiter_injected": False,
        "created_at": BASE_TIME - timedelta(days=2, hours=23, minutes=6),
    },
    {
        "match_key": ("sofia_ramirez", "uhg_data_platform"),
        "role": MessageRole.question,
        "content": COMPANIES[2]["roles"][0]["questions"][0],
        "question_index": 0,
        "recruiter_injected": False,
        "created_at": BASE_TIME - timedelta(days=5, hours=23, minutes=50),
    },
    {
        "match_key": ("sofia_ramirez", "uhg_data_platform"),
        "role": MessageRole.answer,
        "content": (
            "I owned a claims-adjacent ingest flow where late-arriving records could break "
            "operational reports. I added completeness checks, row-level lineage, and rollback "
            "guards so teams could trust daily numbers before publish."
        ),
        "question_index": 0,
        "score": 0.9,
        "score_label": "strong",
        "flags": [],
        "grade_reasoning": "Excellent detail on reliability, controls, and downstream trust.",
        "recruiter_injected": False,
        "created_at": BASE_TIME - timedelta(days=5, hours=23, minutes=43),
    },
    {
        "match_key": ("sofia_ramirez", "uhg_data_platform"),
        "role": MessageRole.question,
        "content": COMPANIES[2]["roles"][0]["questions"][3],
        "question_index": 3,
        "recruiter_injected": False,
        "created_at": BASE_TIME - timedelta(days=5, hours=23, minutes=39),
    },
    {
        "match_key": ("sofia_ramirez", "uhg_data_platform"),
        "role": MessageRole.answer,
        "content": (
            "We used role-based access with clearly documented data contracts, limited "
            "raw PHI access to specific service accounts, and logged every privileged data "
            "movement so audits were straightforward."
        ),
        "question_index": 3,
        "score": 0.83,
        "score_label": "strong",
        "flags": [],
        "grade_reasoning": "Covers access control, auditability, and pragmatic operational safeguards.",
        "recruiter_injected": False,
        "created_at": BASE_TIME - timedelta(days=5, hours=23, minutes=31),
    },
    {
        "match_key": ("sofia_ramirez", "uhg_data_platform"),
        "role": MessageRole.question,
        "content": COMPANIES[2]["roles"][0]["questions"][5],
        "question_index": 5,
        "recruiter_injected": False,
        "created_at": BASE_TIME - timedelta(days=5, hours=23, minutes=27),
    },
    {
        "match_key": ("sofia_ramirez", "uhg_data_platform"),
        "role": MessageRole.answer,
        "content": (
            "I prioritize downstream blast radius, then rollout risk, then engineering effort. "
            "For shared datasets I favor versioned schemas and overlap windows so consumers can "
            "migrate without losing trust in the pipeline."
        ),
        "question_index": 5,
        "score": 0.86,
        "score_label": "strong",
        "flags": [],
        "grade_reasoning": "Strong stakeholder-aware sequencing and good platform judgment.",
        "recruiter_injected": False,
        "created_at": BASE_TIME - timedelta(days=5, hours=23, minutes=20),
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed deterministic Pomelo demo data.")
    parser.add_argument(
        "--reset-only",
        action="store_true",
        help="Delete Pomelo demo rows without reseeding.",
    )
    args = parser.parse_args()

    create_db_and_tables()

    with Session(engine) as session:
        reset_counts = reset_demo_data(session)
        if args.reset_only:
            print_summary("Reset complete", reset_counts)
            return

        seed_counts = seed_demo_data(session)
        print_summary(
            "Seed complete",
            {
                **reset_counts,
                **seed_counts,
                "database_backend": make_url(DATABASE_URL).get_backend_name(),
            },
        )


def reset_demo_data(session: Session) -> dict[str, int]:
    demo_company_ids = set(
        session.exec(
            select(Company.id).where(Company.description.like(f"%{DEMO_MARKER}%"))
        ).all()
    )
    demo_role_ids = set(
        session.exec(select(Role.id).where(Role.company_id.in_(demo_company_ids))).all()
    ) if demo_company_ids else set()
    demo_candidate_ids = set(
        session.exec(
            select(Candidate.id).where(Candidate.email.like(f"%{DEMO_EMAIL_DOMAIN}"))
        ).all()
    )
    demo_match_ids = set(
        session.exec(
            select(Match.id).where(
                sa.or_(
                    Match.candidate_id.in_(demo_candidate_ids) if demo_candidate_ids else sa.false(),
                    Match.role_id.in_(demo_role_ids) if demo_role_ids else sa.false(),
                )
            )
        ).all()
    ) if (demo_candidate_ids or demo_role_ids) else set()

    counts = {
        "deleted_messages": _delete_ids(session, InterviewMessage, "match_id", demo_match_ids),
        "deleted_matches": _delete_ids(session, Match, "id", demo_match_ids),
        "deleted_swipes": _delete_swipes(session, demo_candidate_ids, demo_role_ids),
        "deleted_roles": _delete_ids(session, Role, "id", demo_role_ids),
        "deleted_candidates": _delete_ids(session, Candidate, "id", demo_candidate_ids),
        "deleted_companies": _delete_ids(session, Company, "id", demo_company_ids),
    }
    session.commit()
    return counts


def seed_demo_data(session: Session) -> dict[str, int]:
    companies_by_alias: dict[str, Company] = {}
    roles_by_alias: dict[str, Role] = {}
    candidates_by_alias: dict[str, Candidate] = {}
    swipes_by_key: dict[tuple[str, str], Swipe] = {}
    matches_by_key: dict[tuple[str, str], Match] = {}

    for company_data in COMPANIES:
        company = Company(
            name=company_data["name"],
            description=company_data["description"],
            website=company_data["website"],
            created_at=company_data["created_at"],
        )
        session.add(company)
        session.flush()
        companies_by_alias[company_data["alias"]] = company

        for role_data in company_data["roles"]:
            role = Role(
                company_id=company.id,
                title=role_data["title"],
                description=role_data["description"],
                location=role_data["location"],
                is_remote=role_data["is_remote"],
                min_score=role_data["min_score"],
                max_score=role_data["max_score"],
                keywords=role_data["keywords"],
                questions=role_data["questions"],
                max_swipes_per_day=role_data["max_swipes_per_day"],
                is_active=True,
                created_at=role_data["created_at"],
            )
            session.add(role)
            session.flush()
            roles_by_alias[role_data["alias"]] = role

    for candidate_data in CANDIDATES:
        candidate = Candidate(
            name=candidate_data["name"],
            email=candidate_data["email"],
            resume_text=candidate_data["resume_text"],
            summary=candidate_data["summary"],
            top_skills=candidate_data["top_skills"],
            embedding=build_embedding(candidate_data["embedding_skills"]),
            resume_score=candidate_data["resume_score"],
            created_at=candidate_data["created_at"],
        )
        session.add(candidate)
        session.flush()
        candidates_by_alias[candidate_data["alias"]] = candidate

    for swipe_data in SWIPES:
        swipe = Swipe(
            candidate_id=candidates_by_alias[swipe_data["candidate_alias"]].id,
            role_id=roles_by_alias[swipe_data["role_alias"]].id,
            candidate_direction=swipe_data["candidate_direction"],
            candidate_swiped_at=swipe_data["candidate_swiped_at"],
            recruiter_direction=swipe_data["recruiter_direction"],
            recruiter_swiped_at=swipe_data["recruiter_swiped_at"],
            keyword_score=swipe_data["keyword_score"],
            keyword_reasoning=swipe_data["keyword_reasoning"],
            keyword_approved=swipe_data["keyword_approved"],
            created_at=swipe_data["created_at"],
        )
        session.add(swipe)
        session.flush()
        swipes_by_key[(swipe_data["candidate_alias"], swipe_data["role_alias"])] = swipe

    for match_data in MATCHES:
        key = (match_data["candidate_alias"], match_data["role_alias"])
        match = Match(
            candidate_id=candidates_by_alias[match_data["candidate_alias"]].id,
            role_id=roles_by_alias[match_data["role_alias"]].id,
            swipe_id=swipes_by_key[key].id,
            status=match_data["status"],
            interview_summary=match_data["interview_summary"],
            final_score=match_data["final_score"],
            recommendation=match_data["recommendation"],
            matched_at=match_data["matched_at"],
            completed_at=match_data["completed_at"],
        )
        session.add(match)
        session.flush()
        matches_by_key[key] = match

    for message_data in INTERVIEW_MESSAGES:
        message = InterviewMessage(
            match_id=matches_by_key[message_data["match_key"]].id,
            role=message_data["role"],
            content=message_data["content"],
            question_index=message_data.get("question_index"),
            score=message_data.get("score"),
            score_label=message_data.get("score_label"),
            flags=message_data.get("flags", []),
            grade_reasoning=message_data.get("grade_reasoning"),
            recruiter_injected=message_data.get("recruiter_injected", False),
            created_at=message_data["created_at"],
        )
        session.add(message)

    session.commit()

    return {
        "seeded_companies": len(companies_by_alias),
        "seeded_roles": len(roles_by_alias),
        "seeded_candidates": len(candidates_by_alias),
        "seeded_swipes": len(swipes_by_key),
        "seeded_matches": len(matches_by_key),
        "seeded_messages": len(INTERVIEW_MESSAGES),
    }


def build_embedding(skill_levels: dict[str, float]) -> list[float]:
    vector = [0.0] * len(SKILL_VOCABULARY)
    vocab_index = {skill: idx for idx, skill in enumerate(SKILL_VOCABULARY)}

    for skill, raw_value in skill_levels.items():
        idx = vocab_index.get(skill)
        if idx is None:
            raise ValueError(f"Unknown skill in seed data: {skill}")
        vector[idx] = max(0.0, min(1.0, float(raw_value)))

    return vector


def _delete_ids(session: Session, model: type, field_name: str, ids: Iterable[int]) -> int:
    ids = list(ids)
    if not ids:
        return 0
    result = session.exec(sa.delete(model).where(getattr(model, field_name).in_(ids)))
    return result.rowcount or 0


def _delete_swipes(session: Session, candidate_ids: set[int], role_ids: set[int]) -> int:
    conditions = []
    if candidate_ids:
        conditions.append(Swipe.candidate_id.in_(candidate_ids))
    if role_ids:
        conditions.append(Swipe.role_id.in_(role_ids))
    if not conditions:
        return 0
    result = session.exec(sa.delete(Swipe).where(sa.or_(*conditions)))
    return result.rowcount or 0


def print_summary(title: str, counts: dict[str, int | str]) -> None:
    print(title)
    for key, value in counts.items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
