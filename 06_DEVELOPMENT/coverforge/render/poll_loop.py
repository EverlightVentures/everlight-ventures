"""COVERFORGE e5 render worker.

Polls cover_jobs, renders via produce_assets, uploads to the 'covers' bucket,
marks done/failed (refund on failure). Wraps the unit-tested process_job from
worker.py with real Supabase + provider clients.

RUNS ON e5 ONLY (needs funded FAL_KEY + ANTHROPIC_API_KEY; heavy render).
Deps: pip install -r requirements.txt -r requirements-worker.txt
Env:  SUPABASE_URL, SB_SERVICE_ROLE_KEY, FAL_KEY, ANTHROPIC_API_KEY
"""
import os
import time
import tempfile
from supabase import create_client

from render.render_job import BookMeta
from render.produce import produce_assets
from render.worker import process_job
from render.image_provider import FalFluxProvider
from render.bundle import HaikuLLM

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SB_SERVICE_ROLE_KEY"])
_fal = FalFluxProvider(os.environ["FAL_KEY"])
_llm = HaikuLLM(os.environ["ANTHROPIC_API_KEY"])


class SupaDB:
    def mark_done(self, job_id, outputs):
        sb.table("cover_jobs").update({"status": "done", "outputs": outputs}).eq("id", job_id).execute()

    def mark_failed(self, job_id, err):
        sb.table("cover_jobs").update({"status": "failed", "error": err}).eq("id", job_id).execute()

    def refund(self, job_id):
        row = sb.table("cover_jobs").select("user_id").eq("id", job_id).single().execute()
        sb.table("credit_ledger").insert(
            {"user_id": row.data["user_id"], "delta": 1, "reason": "refund"}
        ).execute()


class SupaStorage:
    def __init__(self, job_id):
        self.job_id = job_id

    def upload(self, local_path):
        key = f"{self.job_id}/{os.path.basename(local_path)}"
        with open(local_path, "rb") as f:
            sb.storage.from_("covers").upload(key, f.read(), {"upsert": "true"})
        return f"covers/{key}"


def build_meta(job):
    i = job["input"]
    trim = tuple(float(x) for x in str(i.get("trim", "6x9")).split("x"))
    return BookMeta(title=i["title"], author=i["author"], genre=i["genre"], vibe=i.get("vibe", ""),
                    trim=trim, page_count=int(i["pageCount"]), paper=i.get("paper", "white"),
                    blurb=i.get("blurb", ""))


def produce(meta, tier):
    out = tempfile.mkdtemp(prefix="cf_")
    return produce_assets(meta, _fal, _llm, out, tier=tier)


def claim_one():
    """Atomically claim one queued job (skip if another worker won the race)."""
    res = sb.table("cover_jobs").select("*").eq("status", "queued").order("created_at").limit(1).execute()
    if not res.data:
        return None
    job = res.data[0]
    upd = sb.table("cover_jobs").update({"status": "running"}).eq("id", job["id"]).eq("status", "queued").execute()
    return job if upd.data else None


def main():
    db = SupaDB()
    while True:
        job = claim_one()
        if not job:
            time.sleep(5)
            continue
        process_job(job, produce=produce, storage=SupaStorage(job["id"]), db=db, build_meta=build_meta)


if __name__ == "__main__":
    main()
