# Everlight Open-Source Repo Stack

This file is the operational guide for expanding Everlight OS with open-source GitHub repos without destabilizing the live stack.

Use the machine-readable registry in `open_source_repo_stack.yaml` and the audit CLI in `open_source_repo_stack.py` to track what is already present and what should be added next.

## Current baseline

Already in the stack:

- `CrewAI` is your orchestration layer.
- `FAISS` is your embedded semantic memory layer.
- `Nengo` is your spiking-neural foundation.
- `spaCy`, `scikit-learn`, and the `neuromorphic/` package already cover local NLP and ML inference.

The next additions should improve local inference, shared memory, web ingestion, and voice workflows without touching the live trading decision path.

## Safe adoption order

### Phase 1: Lowest-risk upgrades

Install these first:

- `LiteLLM` as a single model gateway.
- `Ollama` as the first local LLM runtime.
- `Qdrant` or `pgvector` as the first shared vector store.
- `Crawl4AI` and `Trafilatura` for research and article extraction.
- `Playwright` only for sites that need browser automation.
- `WhisperX` for transcripts and call intelligence.

Why first:

- They directly improve your broker, research, Blinko, and voice flows.
- They can run as sidecars or isolated workers.
- They do not require changing the XLM bot decision engine.

### Phase 2: Controlled expansion

Add these once Phase 1 is stable:

- `LangChain`, `LangGraph`, and `LlamaIndex`
- `llama.cpp` or `llama-cpp-python`
- `LanceDB`
- `Scrapy`
- `whisper.cpp`
- `pyannote-audio`

Why second:

- They help with durable research workflows, richer RAG, and stronger offline inference.
- They add architectural complexity and should sit behind thin adapters.

### Phase 3: Infrastructure-heavy options

Only adopt these if the simpler path is saturated:

- `AutoGen`
- `vLLM`
- `Milvus`
- `Weaviate`

Why last:

- They are powerful, but they add operational overhead.
- They make sense only when throughput, scale, or graph-state requirements justify them.

## Workflow mapping

### Broker pipeline

Recommended stack:

- `Crawl4AI` for seller and buyer site extraction
- `Trafilatura` for article cleanup
- `Qdrant` or `pgvector` for shared memory
- `LlamaIndex` for indexing notes and replies
- `WhisperX` if broker call summaries become part of intake

Owner agents:

- `Benjamin Orozco` for scraping
- `Isaac Ashworth` for indexing and memory
- `Piper Reeves` for outreach-facing consumption
- `Charles Dawson` for analytics
- `Calvin Osei` for broker matching context

### Blinko knowledge base

Recommended stack:

- Keep local `FAISS` for immediate use
- Add `Qdrant` or `pgvector` for shared query access
- Use `LlamaIndex` to ingest notes with metadata
- Use `Crawl4AI` or `Trafilatura` for source cleanup before indexing

Owner agents:

- `Isaac Ashworth`
- `Thomas Rourke`
- `Nathan Ling`

### Local LLM reasoning

Recommended stack:

- `Ollama` first
- `LiteLLM` in front of it
- `llama.cpp` only where tighter low-memory control is needed
- `vLLM` only if GPU throughput becomes the bottleneck

Owner agents:

- `Franklin Steele`
- `Sebastian Torres`
- `Patrick Donovan`

### Voice and Slack workflows

Recommended stack:

- `WhisperX` for timestamped transcription
- `pyannote-audio` for diarization
- `whisper.cpp` for low-footprint offline transcription workers

Owner agents:

- `Rafael Vasquez`
- `Oliver Kessler`
- `Marcus Cole`

## Non-breaking install rules

1. Never install new model-serving or vector infra directly into the live XLM bot environment first.
2. Use a separate venv or container for each new dependency cluster:
   - `local-llm`
   - `vector-memory`
   - `web-ingest`
   - `voice-intel`
3. Put new services behind adapters:
   - `LiteLLM` for model endpoints
   - a memory adapter for `FAISS` / `Qdrant` / `pgvector`
   - a scrape adapter for `Crawl4AI` / `Scrapy` / `Playwright`
4. Promote only after passing:
   - import check
   - one smoke-test task
   - one Slack reporting test
   - one rollback test

## Suggested install sequence for your current system

### 1. Local reasoning

On Oracle E5:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull mistral:7b
pip install -U 'litellm[proxy]'
```

Use:

- CrewAI -> LiteLLM -> Ollama

Do not:

- point production crews straight at a new model runtime without a fallback

### 2. Shared memory

If you want the least friction with your current stack:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Then:

```bash
pip install -U pgvector
```

If you want a separate memory service instead:

```bash
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
pip install -U qdrant-client
```

Use:

- `FAISS` for embedded memory
- `pgvector` or `Qdrant` for shared memory across services

### 3. Research and scraping

```bash
pip install -U crawl4ai trafilatura playwright
playwright install
```

Use:

- `Crawl4AI` first
- `Trafilatura` second
- `Playwright` only when static extraction fails

### 4. Voice intelligence

```bash
pip install -U whisperx pyannote.audio
```

Use:

- `WhisperX` for transcript generation
- `pyannote-audio` for speaker separation

## Registry CLI

List the stack:

```bash
python3 06_DEVELOPMENT/everlight_os/hive_mind/open_source_repo_stack.py list
```

Check what appears to be installed already:

```bash
python3 06_DEVELOPMENT/everlight_os/hive_mind/open_source_repo_stack.py status
```

Print a broker-specific plan:

```bash
python3 06_DEVELOPMENT/everlight_os/hive_mind/open_source_repo_stack.py --workflow broker plan
```

Print a phase-1 plan only:

```bash
python3 06_DEVELOPMENT/everlight_os/hive_mind/open_source_repo_stack.py --phase phase_1 plan
```

## Professional agent naming

Use the formal roster names already defined in `roster.yaml` as the system-of-record.

Preferred examples:

- `Franklin Steele` instead of `Forge Steele`
- `Charles Dawson` instead of `Chart Dawson`
- `Ryan Kim` instead of `Rocket Kim`
- `Calvin Osei` instead of `Cupid Osei`
- `Harrison Knox` instead of `Hammer Knox`

Do not create a parallel naming scheme in new automation. Normalize old aliases to the formal roster names when posting, routing, or logging.
