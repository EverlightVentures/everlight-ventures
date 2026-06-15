# tests/test_worker.py
from render.worker import process_job

class FakeDB:
    def __init__(self): self.done=None; self.failed=None; self.refunded=False
    def mark_done(self, job_id, outputs): self.done=(job_id, outputs)
    def mark_failed(self, job_id, err): self.failed=(job_id, err)
    def refund(self, job_id): self.refunded=True

class FakeStorage:
    def __init__(self): self.uploaded=[]
    def upload(self, path): self.uploaded.append(path); return f"https://cdn/{path.split('/')[-1]}"

class OkResult:  # stand-in for Assets
    class R: wrap_pdf="/t/wrap.pdf"; ebook_pdf="/t/ebook.pdf"; preview_png=None; validation_ok=True
    render=R()
    class B:
        def model_dump(self): return {"keywords":[1]*7}
    bundle=B()

def test_success_uploads_and_marks_done():
    db, st = FakeDB(), FakeStorage()
    process_job({"id":"j1","tier":"paid"}, produce=lambda m,t: OkResult(), storage=st, db=db,
                build_meta=lambda row: object())
    assert db.done and db.done[0]=="j1"
    assert any("wrap.pdf" in u for u in st.uploaded)
    assert db.failed is None

def test_failure_marks_failed_and_refunds():
    db, st = FakeDB(), FakeStorage()
    def boom(m,t): raise RuntimeError("image api down")
    process_job({"id":"j2","tier":"paid"}, produce=boom, storage=st, db=db,
                build_meta=lambda row: object())
    assert db.failed and "image api down" in db.failed[1]
    assert db.refunded is True
