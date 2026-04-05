"""
Computer Use HTTP API Server
Accepts tasks via REST, dispatches to agent, returns results.

POST /task          -- Submit a task for Claude to execute on the virtual desktop
GET  /health        -- Health check
GET  /screenshot    -- Current screenshot (base64)
"""
import os
import json
import base64
import subprocess
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from agent import run_task, take_screenshot

log = logging.getLogger("computer-use-server")
logging.basicConfig(level=logging.INFO)


class TaskRequest(BaseModel):
    task: str
    max_iterations: int = 30


class TaskResponse(BaseModel):
    status: str
    iterations: int
    steps: list
    final_screenshot: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Computer Use API starting...")
    log.info(f"Display: {os.environ.get('DISPLAY', ':99')}")
    log.info(f"Resolution: {os.environ.get('WIDTH', 1280)}x{os.environ.get('HEIGHT', 720)}")
    yield
    log.info("Computer Use API shutting down.")


app = FastAPI(title="Everlight Computer Use API", lifespan=lifespan)


@app.get("/health")
async def health():
    # Check Xvfb is running
    try:
        subprocess.run(["xdotool", "getmouselocation"], timeout=3,
                       env={**os.environ, "DISPLAY": ":99"},
                       capture_output=True, check=True)
        display_ok = True
    except Exception:
        display_ok = False

    return {
        "status": "ok" if display_ok else "degraded",
        "display": display_ok,
        "api_key_set": bool(os.environ.get("ANTHROPIC_API_KEY")),
    }


@app.post("/task", response_model=TaskResponse)
async def submit_task(req: TaskRequest):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not set")

    log.info(f"Task received: {req.task[:100]}...")
    os.environ["MAX_ITERATIONS"] = str(req.max_iterations)

    try:
        result = run_task(req.task)
        return TaskResponse(**result)
    except Exception as e:
        log.error(f"Task failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/screenshot")
async def get_screenshot():
    try:
        b64 = take_screenshot()
        return {"screenshot": b64}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8501)
