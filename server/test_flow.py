#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import uuid
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

import httpx
import websockets
from websockets.exceptions import ConnectionClosed


DEFAULT_HTTP_BASE_URL = "http://0.0.0.0:8000"
DEFAULT_WS_BASE_URL = "ws://0.0.0.0:8000"


@dataclass
class Settings:
    http_base_url: str
    ws_base_url: str
    http_timeout: float
    poll_timeout: float
    poll_interval: float
    sse_connect_timeout: float
    sse_line_timeout: float
    ws_open_timeout: float
    ws_message_timeout: float
    interview_timeout: float
    sse_completion_timeout: float


@dataclass
class SSEState:
    transcript_events: int = 0
    score_events: int = 0
    suggestion_events: int = 0
    final_summary: dict[str, Any] | None = None


def parse_args() -> Settings:
    parser = argparse.ArgumentParser(
        description="Standalone async smoke test for the live Pomelo FastAPI backend."
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("POMELO_BASE_URL", DEFAULT_HTTP_BASE_URL),
        help=f"FastAPI HTTP base URL (default: {DEFAULT_HTTP_BASE_URL})",
    )
    parser.add_argument(
        "--ws-base-url",
        default=os.environ.get("POMELO_WS_BASE_URL", DEFAULT_WS_BASE_URL),
        help=f"FastAPI WebSocket base URL (default: {DEFAULT_WS_BASE_URL})",
    )
    parser.add_argument(
        "--http-timeout",
        type=float,
        default=float(os.environ.get("POMELO_HTTP_TIMEOUT", "180")),
        help="Timeout in seconds for regular HTTP requests.",
    )
    parser.add_argument(
        "--poll-timeout",
        type=float,
        default=float(os.environ.get("POMELO_POLL_TIMEOUT", "20")),
        help="Timeout in seconds while polling for recruiter queue visibility.",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=float(os.environ.get("POMELO_POLL_INTERVAL", "1")),
        help="Seconds between recruiter queue polls.",
    )
    parser.add_argument(
        "--sse-connect-timeout",
        type=float,
        default=float(os.environ.get("POMELO_SSE_CONNECT_TIMEOUT", "20")),
        help="Timeout in seconds while opening the recruiter SSE stream.",
    )
    parser.add_argument(
        "--sse-line-timeout",
        type=float,
        default=float(os.environ.get("POMELO_SSE_LINE_TIMEOUT", "90")),
        help="Timeout in seconds waiting for each recruiter SSE line.",
    )
    parser.add_argument(
        "--ws-open-timeout",
        type=float,
        default=float(os.environ.get("POMELO_WS_OPEN_TIMEOUT", "30")),
        help="Timeout in seconds while opening the candidate WebSocket.",
    )
    parser.add_argument(
        "--ws-message-timeout",
        type=float,
        default=float(os.environ.get("POMELO_WS_MESSAGE_TIMEOUT", "180")),
        help="Timeout in seconds waiting for each candidate WebSocket message.",
    )
    parser.add_argument(
        "--interview-timeout",
        type=float,
        default=float(os.environ.get("POMELO_INTERVIEW_TIMEOUT", "1200")),
        help="Overall timeout in seconds for the candidate interview WebSocket loop.",
    )
    parser.add_argument(
        "--sse-completion-timeout",
        type=float,
        default=float(os.environ.get("POMELO_SSE_COMPLETION_TIMEOUT", "60")),
        help="Extra seconds to wait for the final SSE summary after WS completion.",
    )
    args = parser.parse_args()

    return Settings(
        http_base_url=args.base_url.rstrip("/"),
        ws_base_url=args.ws_base_url.rstrip("/"),
        http_timeout=args.http_timeout,
        poll_timeout=args.poll_timeout,
        poll_interval=args.poll_interval,
        sse_connect_timeout=args.sse_connect_timeout,
        sse_line_timeout=args.sse_line_timeout,
        ws_open_timeout=args.ws_open_timeout,
        ws_message_timeout=args.ws_message_timeout,
        interview_timeout=args.interview_timeout,
        sse_completion_timeout=args.sse_completion_timeout,
    )


def log(step: str, message: str) -> None:
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] [{step}] {message}", flush=True)


def truncate(value: Any, limit: int = 140) -> str:
    text = str(value).replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3]}..."


async def request_json(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    timeout: float,
    expected_status: int | None = None,
    **kwargs: Any,
) -> Any:
    try:
        response = await client.request(method, url, timeout=timeout, **kwargs)
    except httpx.TimeoutException as exc:
        raise RuntimeError(f"{method} {url} timed out after {timeout:.0f}s.") from exc
    except httpx.HTTPError as exc:
        raise RuntimeError(f"{method} {url} failed: {exc}") from exc

    if expected_status is not None and response.status_code != expected_status:
        raise RuntimeError(
            f"{method} {url} returned {response.status_code}, expected {expected_status}: "
            f"{truncate(response.text, 300)}"
        )
    if response.is_error:
        raise RuntimeError(
            f"{method} {url} returned {response.status_code}: {truncate(response.text, 300)}"
        )
    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError(f"{method} {url} returned non-JSON body: {truncate(response.text, 300)}") from exc


def build_resume_text(unique_suffix: str) -> str:
    return f"""Jordan Smoke Test {unique_suffix}
Email: jordan.smoke.{unique_suffix}@example.com

Summary
Software engineer with experience building FastAPI backends, React frontends,
Postgres data models, and event-driven interview tooling for hiring workflows.

Experience
- Led a candidate screening platform rollout used by 4 recruiting teams.
- Built FastAPI APIs, SQLModel persistence, and SSE dashboards for live updates.
- Added WebSocket interview flows, observability, and deterministic smoke tests.
- Improved resume-to-role matching quality by 21 percent with keyword tuning.
- Reduced flaky deploy regressions by 35 percent with integration coverage.

Skills
Python, FastAPI, SQLModel, Postgres, React, TypeScript, WebSockets, SSE,
asyncio, HTTPX, testing, observability, product collaboration.

Projects
- Shipped a recruiter dashboard that streamed transcript and score events live.
- Designed structured interview questions, scoring, and final summary pipelines.
- Wrote clear docs, operational runbooks, and rollout checklists for demos.
"""


async def check_health(client: httpx.AsyncClient, settings: Settings) -> None:
    url = f"{settings.http_base_url}/api/health"
    payload = await request_json(client, "GET", url, timeout=15, expected_status=200)
    if payload.get("status") != "ok":
        raise RuntimeError(f"Health check returned unexpected payload: {payload}")
    log("health", f"url={url} status={payload['status']}")


async def register_candidate(client: httpx.AsyncClient, settings: Settings) -> dict[str, Any]:
    unique_suffix = f"{time.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    name = f"Smoke Test {unique_suffix}"
    email = f"smoke.test.{unique_suffix}@example.com"
    resume_text = build_resume_text(unique_suffix)
    url = f"{settings.http_base_url}/api/candidates/register"
    payload = await request_json(
        client,
        "POST",
        url,
        timeout=settings.http_timeout,
        expected_status=201,
        data={"name": name, "email": email},
        files={"resume": ("resume.txt", resume_text.encode("utf-8"), "text/plain")},
    )
    log(
        "register",
        "candidate_id={id} name={name} score={score} top_skills={skills}".format(
            id=payload.get("id"),
            name=payload.get("name"),
            score=payload.get("score"),
            skills=payload.get("top_skills"),
        ),
    )
    return payload


async def fetch_first_role(
    client: httpx.AsyncClient,
    settings: Settings,
    candidate_id: int,
) -> dict[str, Any]:
    url = f"{settings.http_base_url}/api/candidates/{candidate_id}/feed"
    payload = await request_json(client, "GET", url, timeout=settings.http_timeout, expected_status=200)
    if not isinstance(payload, list):
        raise RuntimeError(f"Candidate feed returned unexpected payload: {payload}")
    if not payload:
        raise RuntimeError(f"Candidate {candidate_id} feed is empty.")
    role = payload[0]
    log(
        "feed",
        "candidate_id={candidate_id} role_id={role_id} title={title} match_percent={match_percent}".format(
            candidate_id=candidate_id,
            role_id=role.get("role_id"),
            title=truncate(role.get("title"), 80),
            match_percent=role.get("match_percent"),
        ),
    )
    return role


async def candidate_like_role(
    client: httpx.AsyncClient,
    settings: Settings,
    candidate_id: int,
    role_id: int,
) -> dict[str, Any]:
    url = f"{settings.http_base_url}/api/swipes"
    payload = await request_json(
        client,
        "POST",
        url,
        timeout=settings.http_timeout,
        expected_status=200,
        json={
            "candidate_id": candidate_id,
            "role_id": role_id,
            "direction": "like",
            "side": "candidate",
        },
    )
    log(
        "candidate-like",
        f"candidate_id={candidate_id} role_id={role_id} matched={payload.get('matched')}",
    )
    return payload


async def wait_for_candidate_in_queue(
    client: httpx.AsyncClient,
    settings: Settings,
    role_id: int,
    candidate_id: int,
) -> dict[str, Any]:
    url = f"{settings.http_base_url}/api/recruiter/roles/{role_id}/candidates"
    deadline = time.monotonic() + settings.poll_timeout
    attempt = 0

    while time.monotonic() < deadline:
        attempt += 1
        payload = await request_json(client, "GET", url, timeout=settings.http_timeout, expected_status=200)
        if not isinstance(payload, list):
            raise RuntimeError(f"Recruiter queue returned unexpected payload: {payload}")
        for candidate in payload:
            if candidate.get("candidate_id") == candidate_id:
                log(
                    "recruiter-queue",
                    "role_id={role_id} candidate_id={candidate_id} found_after_attempt={attempt} "
                    "resume_score_pct={resume_score_pct}".format(
                        role_id=role_id,
                        candidate_id=candidate_id,
                        attempt=attempt,
                        resume_score_pct=candidate.get("resume_score_pct"),
                    ),
                )
                return candidate
        log(
            "recruiter-queue",
            f"role_id={role_id} candidate_id={candidate_id} not_visible_yet attempt={attempt} queue_size={len(payload)}",
        )
        await asyncio.sleep(settings.poll_interval)

    raise RuntimeError(
        f"Candidate {candidate_id} never appeared in recruiter queue for role {role_id} "
        f"within {settings.poll_timeout:.0f}s."
    )


async def run_keyword_filter(
    client: httpx.AsyncClient,
    settings: Settings,
    role_id: int,
    candidate_id: int,
) -> dict[str, Any]:
    url = f"{settings.http_base_url}/api/recruiter/roles/{role_id}/candidates/{candidate_id}/keyword-filter"
    payload = await request_json(client, "POST", url, timeout=settings.http_timeout, expected_status=200)
    log(
        "keyword-filter",
        "candidate_id={candidate_id} role_id={role_id} score={score:.3f} approved={approved} reasoning={reasoning}".format(
            candidate_id=candidate_id,
            role_id=role_id,
            score=float(payload.get("keyword_score", 0.0)),
            approved=payload.get("approve_for_interview"),
            reasoning=truncate(payload.get("reasoning"), 180),
        ),
    )
    return payload


async def recruiter_like_candidate(
    client: httpx.AsyncClient,
    settings: Settings,
    role_id: int,
    candidate_id: int,
) -> int:
    url = f"{settings.http_base_url}/api/recruiter/roles/{role_id}/candidates/{candidate_id}/swipe"
    payload = await request_json(
        client,
        "POST",
        url,
        timeout=settings.http_timeout,
        expected_status=200,
        json={"direction": "like"},
    )
    if not payload.get("matched") or not payload.get("match_id"):
        raise RuntimeError(
            f"Recruiter like did not create a match for candidate {candidate_id} and role {role_id}: {payload}"
        )
    match_id = int(payload["match_id"])
    log("recruiter-like", f"candidate_id={candidate_id} role_id={role_id} match_id={match_id}")
    return match_id


def build_answer_text(message: dict[str, Any], answer_index: int, role_title: str) -> str:
    message_type = message.get("type")
    category = message.get("category")

    behavioral_answers = [
        (
            "I start by aligning on the problem, success metric, and constraints, then I write down a simple "
            "plan with owners and checkpoints. In one project I coordinated product and engineering, shipped a "
            "usable MVP in two weeks, and improved activation by 22 percent without adding incidents because we "
            "used canaries, logging, and a rollback plan."
        ),
        (
            "When I hit ambiguity, I turn it into a short decision memo and review tradeoffs with the team. "
            "That approach helped me unblock a backend migration, reduce duplicate work, and land the change "
            "with zero downtime while keeping recruiters informed through weekly demos and clear status notes."
        ),
        (
            "I like to lead with evidence and close the loop quickly. In a recent workflow redesign I gathered "
            "feedback from users, prioritized the highest-signal gaps, and improved task completion by 18 percent "
            "by simplifying the API contract, tightening validation, and documenting expected edge cases."
        ),
        (
            "My default is to make ownership explicit, keep communication calm, and surface risk early. That "
            "helped our team deliver a live interview feature on time, and we kept the release stable by using "
            "integration checks, dashboards, and a dry run before opening it up broadly."
        ),
    ]

    technical_answers = [
        (
            f"For the {role_title} stack, I would separate the API, persistence, and realtime delivery paths. "
            "I have built FastAPI services backed by Postgres, modeled state changes carefully, and used async "
            "HTTP plus streaming channels so recruiters saw transcript and score updates immediately."
        ),
        (
            "I usually start with correctness, then add observability and backpressure. In practice that meant "
            "idempotent writes, clear status transitions, request timeouts, and tracing around the slow AI calls, "
            "which cut failure rates from 4.2 percent to 0.8 percent during load testing."
        ),
        (
            "My debugging approach is to reproduce the issue deterministically, inspect the event sequence, and "
            "tighten invariants one layer at a time. That worked well for websocket and SSE flows because I could "
            "compare transcript events, score events, and completion signals without guessing where drift started."
        ),
        (
            "I favor simple interfaces that are easy to smoke test end to end. A good example is pairing typed "
            "JSON messages with strict assertions, explicit timeouts, and clear logs so we can catch integration "
            "bugs before opening the browser."
        ),
    ]

    follow_up_answers = [
        (
            "The concrete detail is that I defined the edge cases up front, measured p95 latency and error rate, "
            "and adjusted the rollout once we saw the first bottleneck. That kept the system responsive and gave "
            "the team confidence that the result was repeatable."
        ),
        (
            "A useful example is that I wrote the success criteria before implementation, then checked the live "
            "signals after release. That made it easy to explain why we made each tradeoff and which metric moved."
        ),
    ]

    if message_type == "follow_up":
        choices = follow_up_answers
    elif category == "technical_explain":
        choices = technical_answers
    else:
        choices = behavioral_answers

    return choices[(answer_index - 1) % len(choices)]


async def listen_recruiter_sse(
    client: httpx.AsyncClient,
    settings: Settings,
    match_id: int,
    state: SSEState,
    ready: asyncio.Future[None],
) -> None:
    url = f"{settings.http_base_url}/api/interviews/{match_id}/stream"
    timeout = httpx.Timeout(
        connect=settings.sse_connect_timeout,
        read=None,
        write=settings.http_timeout,
        pool=settings.http_timeout,
    )

    try:
        log("sse", f"connecting url={url}")
        async with client.stream(
            "GET",
            url,
            timeout=timeout,
            headers={"Accept": "text/event-stream"},
        ) as response:
            if response.is_error:
                raise RuntimeError(
                    f"Recruiter SSE returned {response.status_code}: {truncate(await response.aread(), 300)}"
                )
            log("sse", f"connected match_id={match_id}")
            if not ready.done():
                ready.set_result(None)

            lines = response.aiter_lines()
            while True:
                try:
                    line = await asyncio.wait_for(anext(lines), timeout=settings.sse_line_timeout)
                except StopAsyncIteration:
                    raise RuntimeError(
                        f"Recruiter SSE stream closed before final summary for match {match_id}."
                    )
                except asyncio.TimeoutError as exc:
                    raise RuntimeError(
                        f"Recruiter SSE was idle for more than {settings.sse_line_timeout:.0f}s."
                    ) from exc

                if not line:
                    continue
                if line.startswith(":"):
                    continue
                if not line.startswith("data:"):
                    log("sse", f"ignored_line={truncate(line, 160)}")
                    continue

                raw_payload = line[5:].strip()
                try:
                    event = json.loads(raw_payload)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(f"Recruiter SSE sent invalid JSON: {raw_payload}") from exc

                event_type = event.get("type")
                data = event.get("data") or {}

                if event_type == "transcript":
                    state.transcript_events += 1
                    log(
                        "sse-transcript",
                        "role={role} question_id={question_id} text={text}".format(
                            role=data.get("role"),
                            question_id=data.get("question_id"),
                            text=truncate(data.get("text"), 180),
                        ),
                    )
                elif event_type == "score":
                    state.score_events += 1
                    log(
                        "sse-score",
                        "question_id={question_id} score={score} flag={flag} recruiter_hint={hint}".format(
                            question_id=data.get("question_id"),
                            score=data.get("score"),
                            flag=data.get("flag"),
                            hint=truncate(data.get("recruiter_hint"), 160),
                        ),
                    )
                elif event_type == "suggestion":
                    state.suggestion_events += 1
                    log("sse-suggestion", f"text={truncate(data.get('text'), 180)}")
                elif event_type == "interview_complete":
                    summary = data.get("summary")
                    if not isinstance(summary, dict):
                        raise RuntimeError(
                            f"Recruiter SSE interview_complete missing summary payload: {event}"
                        )
                    state.final_summary = summary
                    log(
                        "sse-complete",
                        "verdict={verdict} weighted_score={score} one_liner={one_liner}".format(
                            verdict=summary.get("verdict"),
                            score=summary.get("scores_weighted"),
                            one_liner=truncate(summary.get("one_liner"), 180),
                        ),
                    )
                    return
                else:
                    log("sse", f"unexpected_event_type={event_type} raw={truncate(event, 200)}")
    except Exception as exc:
        if not ready.done():
            ready.set_exception(exc)
        raise


async def run_candidate_interview(
    settings: Settings,
    match_id: int,
    role_title: str,
    sse_task: asyncio.Task[None],
) -> int:
    ws_url = f"{settings.ws_base_url}/api/interviews/{match_id}/ws"
    answers_sent = 0
    first_message = True

    log("ws", f"connecting url={ws_url}")
    try:
        async with websockets.connect(
            ws_url,
            open_timeout=settings.ws_open_timeout,
            close_timeout=5,
            max_size=2_000_000,
        ) as websocket:
            log("ws", f"connected match_id={match_id}")
            while True:
                if sse_task.done():
                    exc = sse_task.exception()
                    if exc is not None:
                        raise RuntimeError(f"Recruiter SSE listener failed during interview: {exc}") from exc

                try:
                    raw_message = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=settings.ws_message_timeout,
                    )
                except asyncio.TimeoutError as exc:
                    raise RuntimeError(
                        f"Candidate WebSocket received no message for {settings.ws_message_timeout:.0f}s."
                    ) from exc

                if isinstance(raw_message, bytes):
                    raise RuntimeError("Candidate WebSocket unexpectedly sent a binary frame.")

                try:
                    message = json.loads(raw_message)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(f"Candidate WebSocket sent invalid JSON: {raw_message}") from exc

                message_type = message.get("type")
                if first_message:
                    log("ws-first", f"type={message_type} payload={truncate(message, 220)}")
                    first_message = False

                if message_type == "error":
                    raise RuntimeError(f"Candidate WebSocket error event: {message.get('detail')}")

                if message_type == "interview_complete":
                    log("ws-complete", f"match_id={match_id} answers_sent={answers_sent}")
                    return answers_sent

                if message_type not in {"question", "follow_up"}:
                    raise RuntimeError(f"Unexpected candidate WebSocket event: {message}")

                prompt_text = str(message.get("text", "")).strip()
                if not prompt_text:
                    raise RuntimeError(f"Candidate WebSocket {message_type} event missing text: {message}")

                log(
                    "ws-prompt",
                    "type={type} id={id} index={index} category={category} text={text}".format(
                        type=message_type,
                        id=message.get("id"),
                        index=message.get("index"),
                        category=message.get("category"),
                        text=truncate(prompt_text, 180),
                    ),
                )

                answer_text = build_answer_text(message, answers_sent + 1, role_title)
                answer_payload = {
                    "type": "answer",
                    "text": answer_text,
                    "elapsed_seconds": 25,
                }
                await websocket.send(json.dumps(answer_payload))
                answers_sent += 1
                log(
                    "ws-answer",
                    "answer_index={index} elapsed_seconds=25 text={text}".format(
                        index=answers_sent,
                        text=truncate(answer_text, 180),
                    ),
                )
    except ConnectionClosed as exc:
        raise RuntimeError(
            f"Candidate WebSocket closed unexpectedly code={exc.code} reason={exc.reason!r}."
        ) from exc


async def run_flow(settings: Settings) -> None:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        await check_health(client, settings)

        registration = await register_candidate(client, settings)
        candidate_id = int(registration["id"])

        role = await fetch_first_role(client, settings, candidate_id)
        role_id = int(role["role_id"])
        role_title = str(role.get("title") or f"role-{role_id}")

        await candidate_like_role(client, settings, candidate_id, role_id)
        await wait_for_candidate_in_queue(client, settings, role_id, candidate_id)
        await run_keyword_filter(client, settings, role_id, candidate_id)
        match_id = await recruiter_like_candidate(client, settings, role_id, candidate_id)

        sse_state = SSEState()
        ready: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        sse_task = asyncio.create_task(
            listen_recruiter_sse(client, settings, match_id, sse_state, ready),
            name=f"recruiter-sse-{match_id}",
        )

        try:
            await asyncio.wait_for(ready, timeout=settings.sse_connect_timeout + 5)
            answers_sent = await asyncio.wait_for(
                run_candidate_interview(settings, match_id, role_title, sse_task),
                timeout=settings.interview_timeout,
            )

            await asyncio.wait_for(sse_task, timeout=settings.sse_completion_timeout)

            if sse_state.final_summary is None:
                raise RuntimeError(f"Recruiter SSE summary never arrived for match {match_id}.")
            if answers_sent < 4:
                raise RuntimeError(
                    f"Interview completed after only {answers_sent} answers; expected at least 4."
                )
            if sse_state.score_events < 4:
                raise RuntimeError(
                    f"Only {sse_state.score_events} score events were observed; expected at least 4."
                )

            summary = sse_state.final_summary
            log(
                "report",
                "candidate_id={candidate_id} role_id={role_id} match_id={match_id} "
                "questions_answered={questions_answered} score_events_seen={score_events_seen} "
                "verdict={verdict}".format(
                    candidate_id=candidate_id,
                    role_id=role_id,
                    match_id=match_id,
                    questions_answered=answers_sent,
                    score_events_seen=sse_state.score_events,
                    verdict=summary.get("verdict"),
                ),
            )
            log(
                "report",
                f"final_summary_one_liner={truncate(summary.get('one_liner'), 220)}",
            )
        finally:
            if not sse_task.done():
                sse_task.cancel()
                with suppress(asyncio.CancelledError):
                    await sse_task


def main() -> int:
    settings = parse_args()
    try:
        asyncio.run(run_flow(settings))
    except KeyboardInterrupt:
        log("error", "Interrupted by user.")
        return 130
    except Exception as exc:
        log("error", str(exc))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
