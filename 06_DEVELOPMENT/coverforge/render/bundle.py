# render/bundle.py
"""KDP listing bundle (keywords, categories, blurb, ad headlines) for one book.
Mirrors the ImageProvider pattern: an LLMClient protocol + offline FakeLLM for
tests + a real HaikuLLM. Pure-text, sub-cent per book."""
from typing import Protocol
from pydantic import BaseModel, Field


class Bundle(BaseModel):
    keywords: list[str] = Field(description="exactly 7 Amazon backend search keywords")
    categories: list[str] = Field(description="exactly 3 Amazon fiction browse categories")
    blurb: str = Field(description="back-cover blurb, 60-120 words")
    ad_headlines: list[str] = Field(description="exactly 5 Amazon Ads headlines, <=30 chars each")


def build_bundle_prompt(meta) -> dict:
    system = (
        "You are a KDP fiction marketing expert. Return EXACTLY 7 backend keywords, "
        "EXACTLY 3 Amazon fiction browse categories, a 60-120 word back-cover blurb, "
        "and EXACTLY 5 Amazon Ads headlines (<=30 chars). Be genre-accurate and concrete."
    )
    user = (
        f"Title: {meta.title}\nAuthor: {meta.author}\nGenre: {meta.genre}\n"
        f"Vibe: {meta.vibe}\nExisting blurb seed: {meta.blurb}"
    )
    return {"system": system, "user": user}


class LLMClient(Protocol):
    def parse(self, system: str, user: str) -> Bundle: ...


class FakeLLM:
    """Deterministic, offline. Shape-valid Bundle for tests."""
    def parse(self, system: str, user: str) -> Bundle:
        return Bundle(
            keywords=[f"kw{i}" for i in range(1, 8)],
            categories=["Fiction > Thriller", "Fiction > Suspense", "Fiction > Crime"],
            blurb="A taut, fast-moving story that keeps the pages turning to the end.",
            ad_headlines=[f"Headline {i}" for i in range(1, 6)],
        )


class HaikuLLM:
    """Real client. Integration-only; not exercised by unit tests."""
    def __init__(self, api_key: str, model: str = "claude-haiku-4-5"):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def parse(self, system: str, user: str) -> Bundle:
        resp = self.client.messages.parse(
            model=self.model, max_tokens=1024, system=system,
            messages=[{"role": "user", "content": user}], output_format=Bundle,
        )
        return resp.parsed_output


def generate_bundle(meta, llm: LLMClient) -> Bundle:
    p = build_bundle_prompt(meta)
    return llm.parse(p["system"], p["user"])
