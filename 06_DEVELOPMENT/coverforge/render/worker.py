# render/worker.py
"""Pure job processor (no live Supabase here - injected db/storage/produce).
The e5 poll loop (Part B / Task B5) wires real Supabase clients into this."""


def process_job(job, produce, storage, db, build_meta):
    """job: a cover_jobs row dict. produce(meta, tier)->Assets. storage.upload(path)->url.
    db.mark_done/mark_failed/refund. Refunds the credit on any failure."""
    try:
        meta = build_meta(job)
        assets = produce(meta, job["tier"])
        outputs = {}
        for attr in ("wrap_pdf", "ebook_pdf", "preview_png"):
            path = getattr(assets.render, attr, None)
            if path:
                outputs[attr] = storage.upload(path)
        if getattr(assets, "bundle", None) is not None:
            outputs["bundle"] = assets.bundle.model_dump()
        if not getattr(assets.render, "validation_ok", True):
            raise RuntimeError("output failed dimension validation")
        db.mark_done(job["id"], outputs)
    except Exception as e:  # never silent-fail; refund the debited credit
        db.mark_failed(job["id"], str(e))
        if job.get("tier") == "paid":
            db.refund(job["id"])
