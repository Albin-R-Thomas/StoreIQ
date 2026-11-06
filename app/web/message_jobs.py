"""Bounded first reply with durable result receipts and restart-safe retry."""

import asyncio
import hashlib

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from app.web import domain, flow
from app.web.store import get, now, put, read_all, transaction

tasks = set()


def key(customer_id, request_id):
    return hashlib.sha256(f"{customer_id}:{request_id}".encode()).hexdigest()


def recover():
    with transaction() as db:
        for job in read_all(db, "message_jobs"):
            if job["status"] == "processing":
                job.update(status="retryable", error="Server restarted. Retry the same message.")
                put(db, "message_jobs", job)
                c = get(db, "customers", job["customer_id"])
                if c:
                    for message in c["messages"]:
                        if message.get("request_id") == job["request_id"]:
                            message["busy_until"] = 0
                    put(db, "customers", c)


async def stop():
    pending = list(tasks)
    for task in pending:
        task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)


async def execute(job, body, user):
    from app.web.api import process_message

    try:
        result = await process_message(job["customer_id"], body, user)
        with transaction() as db:
            saved = get(db, "message_jobs", job["id"])
            saved.update(status="completed", result_customer_id=result["id"], completed_at=now())
            put(db, "message_jobs", saved)
        return result
    except BaseException as exc:
        with transaction() as db:
            saved = get(db, "message_jobs", job["id"])
            saved.update(
                status="retryable",
                status_code=exc.status_code if isinstance(exc, HTTPException) else 503,
                error=exc.detail
                if isinstance(exc, HTTPException)
                else "Processing interrupted. Retry the same message.",
            )
            put(db, "message_jobs", saved)
            c = get(db, "customers", job["customer_id"])
            if c:
                for message in c["messages"]:
                    if message.get("request_id") == body.request_id:
                        message["busy_until"] = 0
                put(db, "customers", c)
        raise


def result(customer_id, request_id, user):
    with transaction() as db:
        domain.owned(db, "customers", customer_id, user)
        job = domain.owned(db, "message_jobs", key(customer_id, request_id), user)
        if job["status"] == "completed":
            return flow.present(db, domain.owned(db, "customers", job["result_customer_id"], user))
        if job["status"] == "retryable":
            return JSONResponse(
                status_code=job.get("status_code", 503),
                content={"detail": job["error"], "retryable": True, "request_id": request_id},
            )
    return receipt(customer_id, request_id)


def receipt(customer_id, request_id):
    from urllib.parse import quote

    return JSONResponse(
        status_code=202,
        content={
            "status": "processing",
            "request_id": request_id,
            "acknowledgement": "Checking the latest details. Your message is saved.",
            "status_url": f"/api/customers/{customer_id}/message-results/{quote(request_id, safe='')}",
        },
        headers={"Retry-After": "1"},
    )


async def submit(customer_id, body, user):
    with transaction() as db:
        domain.owned(db, "customers", customer_id, user)
        job_id = key(customer_id, body.request_id)
        job = get(db, "message_jobs", job_id)
        if job:
            domain.require(
                job["text"] == body.text, "Request ID already used with different content"
            )
            if job["status"] == "processing":
                return receipt(customer_id, body.request_id)
            if job["status"] == "completed":
                return flow.present(
                    db, domain.owned(db, "customers", job["result_customer_id"], user)
                )
        job = {
            "id": job_id,
            "customer_id": customer_id,
            "request_id": body.request_id,
            "owner": user["id"],
            "text": body.text,
            "status": "processing",
            "created_at": now(),
        }
        put(db, "message_jobs", job)
    task = asyncio.create_task(execute(job, body, user))
    tasks.add(task)

    def done(completed):
        tasks.discard(completed)
        if not completed.cancelled():
            completed.exception()  # Result errors remain in the durable receipt.

    task.add_done_callback(done)
    ready, _ = await asyncio.wait({task}, timeout=1.5)
    if ready:
        return task.result()
    return receipt(customer_id, body.request_id)
