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
    AuthUser,
    Candidate,
    Company,
    InterviewMessage,
    Match,
    MatchStatus,
    MessageRole,
    Role,
    Swipe,
    SwipeDirection,
    UserRole,
)
from services.auth_service import hash_password
from services.resume_service import SKILL_VOCABULARY

DEMO_MARKER = "[Pomelo demo seed]"
DEMO_EMAIL_DOMAIN = "@demo.pomelo.test"
DEMO_PASSWORD = "pomelo2026"
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
            "Recent CS grad with a summer internship in applied ML, hands-on coursework "
            "in deep learning, and personal projects building small AI-powered tools with "
            "Python and FastAPI."
        ),
        "top_skills": ["Python", "PyTorch", "FastAPI", "TypeScript", "Machine Learning"],
        "resume_score": 0.76,
        "resume_text": (
            "Mira Patel graduated last spring with a CS degree focused on machine learning. "
            "During her junior-year internship she helped build a simple retrieval prototype "
            "in Python and wrote a few FastAPI endpoints. She has taken two graduate-level ML "
            "courses, worked through PyTorch tutorials, and built a small personal project "
            "that uses a language model to summarize notes. She is looking for her first "
            "full-time role in applied AI."
        ),
        "embedding_skills": {
            "Python": 0.78,
            "TypeScript": 0.45,
            "FastAPI": 0.62,
            "React": 0.38,
            "PyTorch": 0.65,
            "REST API": 0.55,
            "System Design": 0.40,
            "Machine Learning": 0.72,
            "PostgreSQL": 0.30,
            "AWS": 0.25,
            "Git": 0.60,
        },
        "created_at": BASE_TIME - timedelta(days=16, hours=1),
    },
    {
        "alias": "ethan_brooks",
        "name": "Ethan Brooks",
        "email": "ethan.brooks@demo.pomelo.test",
        "summary": (
            "Recent CS grad with a fintech internship, solid Java coursework, and "
            "personal projects in React and PostgreSQL. Eager to grow in backend "
            "financial software."
        ),
        "top_skills": ["Java", "TypeScript", "React", "PostgreSQL", "AWS"],
        "resume_score": 0.65,
        "resume_text": (
            "Ethan Brooks just finished his CS degree and completed one internship at a "
            "small fintech company where he fixed bugs in a Java service and helped add "
            "a few API endpoints. He built a React budgeting app as a class project, "
            "has used PostgreSQL in coursework, and is comfortable with Git and basic "
            "AWS deployments from tutorials. He is looking for his first full-time "
            "software engineering role."
        ),
        "embedding_skills": {
            "Java": 0.68,
            "TypeScript": 0.50,
            "React": 0.55,
            "SQL": 0.62,
            "PostgreSQL": 0.58,
            "AWS": 0.38,
            "Microservices": 0.30,
            "Security": 0.28,
            "REST API": 0.55,
            "Git": 0.65,
        },
        "created_at": BASE_TIME - timedelta(days=15, hours=7),
    },
    {
        "alias": "sofia_ramirez",
        "name": "Sofia Ramirez",
        "email": "sofia.ramirez@demo.pomelo.test",
        "summary": (
            "Recent data science grad with internship experience cleaning and loading "
            "health-related datasets, solid SQL and Python fundamentals, and a "
            "capstone project using Spark."
        ),
        "top_skills": ["Python", "SQL", "Spark", "Data Engineering", "AWS"],
        "resume_score": 0.68,
        "resume_text": (
            "Sofia Ramirez graduated with a data science degree and spent one summer as "
            "a data intern at a healthcare software company where she wrote SQL queries, "
            "cleaned CSV datasets in Python, and helped document a data pipeline. Her "
            "senior capstone used PySpark to process a public health dataset. She has "
            "basic AWS knowledge from class, uses Git regularly, and is excited to grow "
            "into a data engineering role."
        ),
        "embedding_skills": {
            "Python": 0.70,
            "SQL": 0.74,
            "Spark": 0.55,
            "PostgreSQL": 0.48,
            "Data Engineering": 0.62,
            "AWS": 0.35,
            "CI/CD": 0.28,
            "Security": 0.25,
            "Pandas": 0.65,
            "Git": 0.60,
        },
        "created_at": BASE_TIME - timedelta(days=14, hours=3),
    },
    {
        "alias": "jordan_lee",
        "name": "Jordan Lee",
        "email": "jordan.lee@demo.pomelo.test",
        "summary": (
            "Bootcamp grad with several self-directed React and Node.js projects, "
            "comfortable with TypeScript and REST APIs, looking for a first junior "
            "frontend or full-stack role."
        ),
        "top_skills": ["TypeScript", "React", "Node.js", "GraphQL", "System Design"],
        "resume_score": 0.58,
        "resume_text": (
            "Jordan Lee completed a full-stack web development bootcamp and has been "
            "building projects since. He made a React task-tracking app with a Node.js "
            "backend, experimented with a small GraphQL API following a tutorial, and "
            "deployed a couple of sites to basic hosting. He is learning TypeScript and "
            "has read about system design but has not applied it professionally yet. "
            "He is looking for a junior role where he can keep growing."
        ),
        "embedding_skills": {
            "TypeScript": 0.52,
            "React": 0.65,
            "Node.js": 0.58,
            "GraphQL": 0.38,
            "REST API": 0.55,
            "System Design": 0.28,
            "AWS": 0.22,
            "Security": 0.18,
            "HTML": 0.72,
            "CSS": 0.68,
        },
        "created_at": BASE_TIME - timedelta(days=13, hours=9),
    },
    {
        "alias": "priya_nair",
        "name": "Priya Nair",
        "email": "priya.nair@demo.pomelo.test",
        "summary": (
            "Finance major who picked up Python and SQL through coursework and a "
            "part-time analyst role, now pivoting into data engineering with a "
            "basic Spark background."
        ),
        "top_skills": ["Python", "SQL", "PostgreSQL", "Spark", "Security"],
        "resume_score": 0.62,
        "resume_text": (
            "Priya Nair studied finance and taught herself Python and SQL to handle "
            "data tasks in a part-time analyst job where she built Excel-to-SQL "
            "reporting scripts and cleaned up a few PostgreSQL tables. She took an "
            "online Spark course last semester and completed its exercises. She is "
            "methodical and takes data quality seriously, and is looking to transition "
            "fully into a data engineering role."
        ),
        "embedding_skills": {
            "Python": 0.58,
            "SQL": 0.72,
            "PostgreSQL": 0.60,
            "Spark": 0.42,
            "Data Engineering": 0.45,
            "AWS": 0.22,
            "Security": 0.32,
            "Git": 0.50,
            "Pandas": 0.55,
        },
        "created_at": BASE_TIME - timedelta(days=12, hours=11),
    },
    {
        "alias": "caleb_wright",
        "name": "Caleb Wright",
        "email": "caleb.wright@demo.pomelo.test",
        "summary": (
            "Self-taught frontend developer with React and CSS projects on GitHub, "
            "comfortable consuming REST APIs, still building backend confidence."
        ),
        "top_skills": ["TypeScript", "React", "Node.js", "CSS", "REST API"],
        "resume_score": 0.50,
        "resume_text": (
            "Caleb Wright taught himself web development through YouTube and freeCodeCamp. "
            "He has built a few React hobby projects, styled them with CSS, and learned "
            "how to call REST APIs from the frontend. He followed a Node.js tutorial to "
            "add a simple backend to one project and has dabbled in GraphQL through an "
            "online course. He is entry-level and knows his backend skills need work."
        ),
        "embedding_skills": {
            "TypeScript": 0.45,
            "React": 0.68,
            "Node.js": 0.35,
            "CSS": 0.72,
            "REST API": 0.50,
            "HTML": 0.75,
            "GraphQL": 0.25,
            "Git": 0.55,
        },
        "created_at": BASE_TIME - timedelta(days=11, hours=5),
    },
    {
        "alias": "hannah_chen",
        "name": "Hannah Chen",
        "email": "hannah.chen@demo.pomelo.test",
        "summary": (
            "CS student who ran campus Linux servers, learned Docker and Kubernetes "
            "through side projects, and is looking for a first DevOps or platform role."
        ),
        "top_skills": ["Go", "Kubernetes", "Docker", "AWS", "CI/CD"],
        "resume_score": 0.44,
        "resume_text": (
            "Hannah Chen is finishing her CS degree and has spent the last year as a "
            "volunteer sysadmin for her university's student computing club, keeping "
            "Linux servers running and setting up Docker containers for club projects. "
            "She went through a Kubernetes tutorial, deployed a small app on a free "
            "cloud tier, and wrote a short Go script to automate a repetitive task. "
            "She has no professional DevOps experience yet but learns quickly and wants "
            "to grow into platform engineering."
        ),
        "embedding_skills": {
            "Go": 0.32,
            "Kubernetes": 0.48,
            "Docker": 0.62,
            "AWS": 0.28,
            "Linux": 0.65,
            "CI/CD": 0.42,
            "System Design": 0.20,
            "Git": 0.58,
        },
        "created_at": BASE_TIME - timedelta(days=10, hours=13),
    },
    {
        "alias": "leo_martinez",
        "name": "Leo Martinez",
        "email": "leo.martinez@demo.pomelo.test",
        "summary": (
            "Junior in college with one part-time internship, still building core "
            "skills in Python and web basics, looking for a role with mentorship."
        ),
        "top_skills": ["Python", "HTML", "CSS", "Git"],
        "resume_score": 0.28,
        "resume_text": (
            "Leo Martinez is a junior studying information systems. Last semester he "
            "did a part-time internship where he updated content on an internal HTML "
            "dashboard and wrote a short Python script to rename files in bulk. He "
            "knows basic CSS from a web design class, uses Git for class projects, "
            "and is comfortable asking for help. He is looking for an internship or "
            "entry-level role with strong mentorship."
        ),
        "embedding_skills": {
            "Python": 0.28,
            "HTML": 0.38,
            "CSS": 0.32,
            "Git": 0.30,
        },
        "created_at": BASE_TIME - timedelta(days=9, hours=4),
    },
    {
        "alias": "alex_rivera",
        "name": "Alex Rivera",
        "email": "alex.rivera@demo.pomelo.test",
        "summary": (
            "Full-stack engineer with four years at a B2B SaaS startup, comfortable "
            "owning React frontends and Node.js APIs end to end, with solid PostgreSQL "
            "and AWS experience from real product work."
        ),
        "top_skills": ["TypeScript", "React", "Node.js", "PostgreSQL", "AWS"],
        "resume_score": 0.82,
        "resume_text": (
            "Alex Rivera spent four years as a software engineer at a mid-size SaaS "
            "company building customer-facing dashboards in React and TypeScript and "
            "maintaining the Node.js services behind them. He owns features from "
            "database query to UI, has dealt with slow PostgreSQL queries and on-call "
            "incidents, and set up CI/CD pipelines on AWS. He is comfortable working "
            "without much hand-holding but still defers to senior engineers on "
            "architecture decisions. Looking for a role with a stronger product mission "
            "and a bigger team."
        ),
        "embedding_skills": {
            "TypeScript": 0.88,
            "React": 0.85,
            "Node.js": 0.82,
            "GraphQL": 0.55,
            "REST API": 0.80,
            "System Design": 0.60,
            "AWS": 0.68,
            "Security": 0.52,
            "PostgreSQL": 0.75,
            "SQL": 0.72,
            "CI/CD": 0.60,
            "Git": 0.85,
        },
        "created_at": BASE_TIME - timedelta(days=8, hours=6),
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
        "keyword_score": 0.74,
        "keyword_reasoning": (
            "Python and ML coursework align with the role keywords, and the internship "
            "retrieval project shows early applied AI interest. Limited production depth "
            "but a strong foundation for an entry-level hire."
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
        "keyword_score": 0.65,
        "keyword_reasoning": (
            "Java coursework and fintech internship touch the right keywords. Backend "
            "depth is limited but the fundamentals are there for a junior banking role."
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
        "keyword_score": 0.68,
        "keyword_reasoning": (
            "SQL and Python internship work matches data platform keywords. Spark is "
            "coursework-level only, but the healthcare dataset exposure is a plus for "
            "an entry-level data engineering candidate."
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
        "keyword_score": 0.62,
        "keyword_reasoning": (
            "SQL and Python keyword match is decent given her analyst background. "
            "Spark is self-taught and shallow. Worth a recruiter look for a junior opening."
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
        "keyword_score": 0.46,
        "keyword_reasoning": (
            "Docker and Linux club experience maps to some platform keywords, but "
            "Kubernetes and Go are tutorial-level only. Marginal fit for an inference "
            "platform role without more hands-on experience."
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
        "keyword_score": 0.42,
        "keyword_reasoning": (
            "React and HTML are there but everything else is tutorial-level. The role "
            "needs more backend depth and security awareness than this profile shows."
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
        "keyword_score": 0.22,
        "keyword_reasoning": (
            "HTML and Python basics do not meet the keyword bar for a banking platform role. "
            "No Java, SQL, or security background in evidence."
        ),
        "keyword_approved": False,
        "created_at": BASE_TIME - timedelta(days=1, hours=20),
    },
    {
        "candidate_alias": "alex_rivera",
        "role_alias": "openai_applied_ai",
        "candidate_direction": SwipeDirection.like,
        "candidate_swiped_at": BASE_TIME - timedelta(days=2, hours=4),
        "recruiter_direction": SwipeDirection.like,
        "recruiter_swiped_at": BASE_TIME - timedelta(days=2, hours=1),
        "keyword_score": 0.84,
        "keyword_reasoning": (
            "Strong product engineering background with clear React, TypeScript, API, "
            "PostgreSQL, and AWS overlap. Less direct ML depth than the role ideal, but "
            "solid evidence of shipping product workflows end to end."
        ),
        "keyword_approved": True,
        "created_at": BASE_TIME - timedelta(days=2, hours=4),
    },
    {
        "candidate_alias": "alex_rivera",
        "role_alias": "uhg_member_experience",
        "candidate_direction": SwipeDirection.like,
        "candidate_swiped_at": BASE_TIME - timedelta(days=1, hours=10),
        "recruiter_direction": SwipeDirection.like,
        "recruiter_swiped_at": BASE_TIME - timedelta(hours=22),
        "keyword_score": 0.86,
        "keyword_reasoning": (
            "Strong TypeScript, React, Node.js, and REST API overlap with the role. "
            "Four years of product ownership is a clear signal for a member-experience "
            "engineering role."
        ),
        "keyword_approved": True,
        "created_at": BASE_TIME - timedelta(days=1, hours=10),
    },
]

MATCHES = [
    {
        "candidate_alias": "alex_rivera",
        "role_alias": "openai_applied_ai",
        "status": MatchStatus.interviewing,
        "matched_at": BASE_TIME - timedelta(days=2),
        "completed_at": None,
        "final_score": None,
        "recommendation": None,
        "interview_summary": None,
    },
    {
        "candidate_alias": "alex_rivera",
        "role_alias": "uhg_member_experience",
        "status": MatchStatus.pending,
        "matched_at": BASE_TIME - timedelta(hours=22),
        "completed_at": None,
        "final_score": None,
        "recommendation": None,
        "interview_summary": None,
    },
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
                "behavioral_score": 0.72,
                "communication_score": 0.75,
                "concerns": [
                    "Spark experience is coursework-level only — has not run jobs on real production data.",
                    "Answers stayed close to her internship and class projects; struggled to generalize to new scenarios.",
                ],
                "confidence": 0.70,
                "flags_summary": [],
                "interviewer_notes": {
                    "do_not_ask_again": [
                        "Internship data cleaning work",
                        "Capstone project details",
                    ],
                    "suggested_opener": (
                        "Ask how she would approach learning a new data pipeline codebase on her first week."
                    ),
                    "topics_to_probe": [
                        "How she handles ambiguity without a supervisor nearby",
                        "Comfort with reading and writing SQL for unfamiliar schemas",
                    ],
                },
                "one_liner": (
                    "Motivated entry-level candidate with the right fundamentals; needs hands-on pipeline experience to grow into the role."
                ),
                "scores_weighted": 0.71,
                "strengths": [
                    "Clear communicator who explains her reasoning step by step",
                    "Genuinely curious about data quality and documentation",
                    "SQL and Python basics are solid for someone at this stage",
                ],
                "technical_score": 0.68,
                "verdict": "ADVANCE",
            },
            sort_keys=True,
        ),
    },
]

INTERVIEW_MESSAGES = [
    {
        "match_key": ("alex_rivera", "openai_applied_ai"),
        "role": MessageRole.question,
        "content": COMPANIES[0]["roles"][0]["questions"][0],
        "question_index": 0,
        "recruiter_injected": False,
        "created_at": BASE_TIME - timedelta(days=1, hours=23, minutes=54),
    },
    {
        "match_key": ("alex_rivera", "openai_applied_ai"),
        "role": MessageRole.answer,
        "content": (
            "At my last company I led a workflow that summarized account activity for customer success managers. "
            "I owned the API layer, prompt orchestration, and the React surface where teams reviewed outputs. "
            "We tracked acceptance rate, edit rate, and the percentage of summaries that needed manual correction "
            "before sharing them with customers, and we used those signals to tighten prompts and fallback logic."
        ),
        "question_index": 0,
        "score": 0.86,
        "score_label": "strong",
        "flags": [],
        "grade_reasoning": "Clear end-to-end ownership with concrete product metrics and iteration loop.",
        "recruiter_injected": False,
        "created_at": BASE_TIME - timedelta(days=1, hours=23, minutes=47),
    },
    {
        "match_key": ("alex_rivera", "openai_applied_ai"),
        "role": MessageRole.question,
        "content": COMPANIES[0]["roles"][0]["questions"][1],
        "question_index": 1,
        "recruiter_injected": False,
        "created_at": BASE_TIME - timedelta(days=1, hours=23, minutes=42),
    },
    {
        "match_key": ("alex_rivera", "openai_applied_ai"),
        "role": MessageRole.answer,
        "content": (
            "I usually start by making the request testable. I translate the vague ask into a few user jobs, define what failure looks like, "
            "and build a small set of examples that represent the happy path plus likely edge cases. From there I separate offline checks "
            "like rubric scoring or pairwise review from online metrics like task completion, edits, latency, and support tickets."
        ),
        "question_index": 1,
        "score": 0.82,
        "score_label": "strong",
        "flags": [],
        "grade_reasoning": "Strong product framing with concrete evaluation structure and rollout metrics.",
        "recruiter_injected": False,
        "created_at": BASE_TIME - timedelta(days=1, hours=23, minutes=35),
    },
    {
        "match_key": ("alex_rivera", "openai_applied_ai"),
        "role": MessageRole.question,
        "content": COMPANIES[0]["roles"][0]["questions"][2],
        "question_index": 2,
        "recruiter_injected": False,
        "created_at": BASE_TIME - timedelta(days=1, hours=23, minutes=29),
    },
    {
        "match_key": ("alex_rivera", "openai_applied_ai"),
        "role": MessageRole.answer,
        "content": (
            "One service I owned became too slow after we added heavier enrichment steps. I profiled where time was going, moved repeated lookups "
            "behind caching, tightened a couple of expensive database queries, and added structured timing logs around the slowest steps. "
            "That got our p95 down enough that the feature felt reliable again without having to remove useful context."
        ),
        "question_index": 2,
        "score": 0.79,
        "score_label": "strong",
        "flags": [],
        "grade_reasoning": "Good production ownership and latency reasoning with credible operational detail.",
        "recruiter_injected": False,
        "created_at": BASE_TIME - timedelta(days=1, hours=23, minutes=22),
    },
    {
        "match_key": ("alex_rivera", "openai_applied_ai"),
        "role": MessageRole.question,
        "content": COMPANIES[0]["roles"][0]["questions"][4],
        "question_index": 4,
        "recruiter_injected": False,
        "created_at": BASE_TIME - timedelta(days=1, hours=23, minutes=16),
    },
    {
        "match_key": ("alex_rivera", "openai_applied_ai"),
        "role": MessageRole.answer,
        "content": (
            "I would instrument it so different teams can trust it for different reasons: product sees adoption and completion, engineering sees latency "
            "and failure budgets, and safety or QA sees sampled outputs with reasons for overrides. I also like staged rollout flags so we can compare "
            "behavior across cohorts before making the feature fully default."
        ),
        "question_index": 4,
        "score": 0.81,
        "score_label": "strong",
        "flags": [],
        "grade_reasoning": "Thoughtful answer that balances observability, product rollout, and trust-building concerns.",
        "recruiter_injected": False,
        "created_at": BASE_TIME - timedelta(days=1, hours=23, minutes=9),
    },
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
            "During my internship I helped build a small retrieval prototype — I wrote the "
            "FastAPI endpoints and helped run some basic accuracy checks on the outputs. "
            "My mentor reviewed the evals but I learned a lot about what to look for."
        ),
        "question_index": 0,
        "score": 0.62,
        "score_label": "adequate",
        "flags": [],
        "grade_reasoning": "Shows relevant internship exposure but ownership was shared and depth is limited.",
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
            "I think I would start by writing down what the feature is supposed to do and "
            "maybe test it on a few example inputs. I have not done this professionally "
            "yet but in my ML course we would check accuracy on a held-out set before calling something done."
        ),
        "question_index": 1,
        "score": 0.48,
        "score_label": "adequate",
        "flags": [],
        "grade_reasoning": "Answer is conceptually on track but relies on coursework framing and lacks practical detail.",
        "recruiter_injected": False,
        "created_at": BASE_TIME - timedelta(days=2, hours=23, minutes=25),
    },
    {
        "match_key": ("mira_patel", "openai_applied_ai"),
        "role": MessageRole.follow_up,
        "content": "What would you do differently if the same prototype needed to handle ten times the input variety?",
        "question_index": None,
        "recruiter_injected": True,
        "created_at": BASE_TIME - timedelta(days=2, hours=23, minutes=22),
    },
    {
        "match_key": ("mira_patel", "openai_applied_ai"),
        "role": MessageRole.answer,
        "content": (
            "I think I would add more varied examples to the test set and maybe try a few "
            "different prompts to see which one handled the edge cases better. I am not "
            "sure exactly how I would set that up at scale but that is what I would start with."
        ),
        "question_index": None,
        "score": 0.45,
        "score_label": "adequate",
        "flags": [],
        "grade_reasoning": "Reasonable instinct but vague — no concrete plan for handling scale or systematic eval.",
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
            "I have not worked on a production service yet, but in my internship the "
            "prototype was slow and my mentor suggested caching some of the repeated lookups. "
            "I helped implement that and it did seem faster, but I did not measure it formally."
        ),
        "question_index": 2,
        "score": 0.40,
        "score_label": "weak",
        "flags": ["no_production_experience"],
        "grade_reasoning": "Describes a valid concept but entirely anecdotal with no ownership or measurement.",
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
            "In my internship I worked on a pipeline that loaded patient visit data into "
            "a warehouse table. I noticed some rows were duplicated and wrote a SQL check "
            "to catch them before the load. My supervisor helped me add it to the pipeline."
        ),
        "question_index": 0,
        "score": 0.65,
        "score_label": "adequate",
        "flags": [],
        "grade_reasoning": "Relevant internship example with concrete SQL work, though ownership was supervised.",
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
            "I know sensitive data should be restricted so not everyone can see it. "
            "At my internship we used different database users with different permissions "
            "but I was not the one setting that up — I just knew I could only read, not write."
        ),
        "question_index": 3,
        "score": 0.42,
        "score_label": "weak",
        "flags": ["limited_security_depth"],
        "grade_reasoning": "Aware of access control at a surface level but no hands-on experience designing controls.",
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
            "I would probably talk to whoever uses the dataset first to see how urgent "
            "their needs are, then try to make the change in a way that does not break "
            "their existing queries. I am not sure what the right process is exactly."
        ),
        "question_index": 5,
        "score": 0.50,
        "score_label": "adequate",
        "flags": [],
        "grade_reasoning": "Instinct to consult stakeholders is good but no concrete approach to schema migration.",
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
        "deleted_auth_users": _delete_demo_auth_users(session),
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

    # ----- demo auth users -----
    hashed = hash_password(DEMO_PASSWORD)
    demo_auth_users = [
        AuthUser(
            email="mira.patel@demo.pomelo.test",
            hashed_password=hashed,
            role=UserRole.candidate,
            candidate_id=candidates_by_alias["mira_patel"].id,
        ),
        AuthUser(
            email="alex.rivera@demo.pomelo.test",
            hashed_password=hashed,
            role=UserRole.candidate,
            candidate_id=candidates_by_alias["alex_rivera"].id,
        ),
        AuthUser(
            email="recruiter@openai.demo.pomelo.test",
            hashed_password=hashed,
            role=UserRole.recruiter,
            company_id=companies_by_alias["openai"].id,
        ),
        AuthUser(
            email="recruiter@goldman.demo.pomelo.test",
            hashed_password=hashed,
            role=UserRole.recruiter,
            company_id=companies_by_alias["goldman"].id,
        ),
    ]
    for auth_user in demo_auth_users:
        session.add(auth_user)

    session.commit()

    return {
        "seeded_companies": len(companies_by_alias),
        "seeded_roles": len(roles_by_alias),
        "seeded_candidates": len(candidates_by_alias),
        "seeded_swipes": len(swipes_by_key),
        "seeded_matches": len(matches_by_key),
        "seeded_messages": len(INTERVIEW_MESSAGES),
        "seeded_auth_users": len(demo_auth_users),
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


def _delete_demo_auth_users(session: Session) -> int:
    result = session.exec(
        sa.delete(AuthUser).where(AuthUser.email.like("%demo.pomelo.test"))
    )
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
