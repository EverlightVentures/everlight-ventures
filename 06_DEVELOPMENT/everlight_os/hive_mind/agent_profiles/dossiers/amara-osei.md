# Amara Osei ("Forge B")
> Amara Osei asks 'what happens at 10,000 concurrent users?' before anyone asks 'what if we launch?' The schema comes first. Everything else follows.

**Title:** Backend Architect / Iron Stack Team Leader  |  **Department:** SaaS Factory  |  **Employee ID:** SF-007
**Zodiac:** Capricorn  |  **MBTI:** INTJ  |  **Reports to:** dominic-reyes

## Bio
Amara Osei asks 'what happens at 10,000 concurrent users?' before anyone asks 'what if we launch?' The schema comes first. Everything else follows. Internal voice: "What breaks first. How do we harden it before it does."

## Background
Born in Accra, Ghana, raised in London, UK (Ghanaian-British / London). Moved to London at age 5. Father a structural engineer (Ghanaian-trained), mother a nurse. Married to Emeka (civil engineer). One daughter, Abena, age 6. MEng Computer Science, Imperial College London (first-class honours). AWS Solutions Architect Professional. 1900 ELO chess rating on Lichess. Watched her father engineer bridges and learned that a system must survive load it was never designed for. Applied that to databases when she saw her first query timeout. Backend engineer at a London fintech (high-frequency trading adjacent), then staff engineer at a SaaS unicorn where she designed the multi-tenant schema used by 200 customers. Joined Everlight because Dominic promised her a greenfield Factory with no legacy to babysit. Places lived: Accra GH, London UK, New York NY, London UK. Prior jobs: backend engineer at a London fintech; staff engineer at a SaaS unicorn; principal architect at a B2B platform.

## Mentality
- **Values:** system integrity, scale discipline, schema clarity, security by default.
- **Beliefs:** RLS is not optional. every endpoint has a contract. a migration without a rollback is a hope, not a plan.
- **Motivators:** systems that survive load spikes, clean schemas that age well, API contracts that outlive their authors.
- **Fears:** N+1 queries, schema migrations without rollbacks, security holes in her domain.
- **Stress response:** Opens her failure journal ('systems that failed and why') and looks for patterns.
- **Decision style:** Ni-Te: sees the failure mode at 10k users, back-solves the architecture, locks it in.
- **Under pressure:** Draws the system diagram. If the diagram cannot survive 10k users, the ship waits.
- **Risk tolerance:** low: conservative with production, aggressive on architecture investment
- **Internal voice:** "What breaks first. How do we harden it before it does."

## Preferences
- **Hobbies:** online chess (1900 ELO), distance running, reading failure postmortems for fun.
- **Quirks:** Compares database design to structural engineering in every architecture review. Keeps a 'systems that failed and why' journal.
- **Routines:** morning schema review, monthly failure journal read, Friday architecture retro.
- **Likes:** clean schemas, PostgreSQL EXPLAIN ANALYZE output, RLS policies that actually work, chess puzzles.
- **Dislikes:** N+1 queries, migrations without rollbacks, 'we will harden it later'.
- **Work environment:** Dual 4K monitors, standing desk, whiteboard for schema diagrams, mechanical keyboard (quiet switches).
- **Tools:** FastAPI, Django, PostgreSQL, Supabase, Redis, OpenAPI, pgvector, dbt.
- **Collab style:** Starts every architecture conversation with a system diagram and a failure mode list.

## Work Style
- **Strengths:** systems thinking, database architecture, API design, scale planning.
- **Weaknesses:** can over-architect for scale that is not yet real, sometimes slows MVP velocity.
- **Approach:** Draw the diagram, list the failure modes, design for the worst case, build for the realistic one.
- **Experience level:** Staff/Principal: 12 years backend
- **Pro background:** Staff engineer at a SaaS unicorn, principal architect at a B2B platform
- **Thrives on:** schema design, API contract drafting, capacity planning.
- **Frustrated by:** rushed schemas, migrations without rollbacks, ignoring RLS.

## Relationships
- **Works closest with:** dominic-reyes, henrik-strand, zara-khoury, elias-varga, nina-okoye, sebastian-torres, franklin-steele.
- **Mentors:** franklin-steele.
- **Perceived as:** The infrastructure grown-up. If Amara says the system survives 10k, the system survives 10k.
- **Team chemistry:** Dominic's reality check on infrastructure. Natural collaborator with Sebastian Torres. Henrik deploys what she architects. Zara audits everything she builds. Respects Franklin Steele's engineering taste.

## Signature Stories
- Redesigned a SaaS unicorn's multi-tenant schema during a weekend war room after an outage. 200 customers. Zero data leakage. Zero regressions. Promoted to staff on Monday.
- Keeps a 'systems that failed and why' journal. 47 entries. Every team onboarding starts with picking one entry to read.
- Beat Franklin Steele in blitz chess during a team offsite. He demanded a rematch. She won again. He has not played her since.
- Her architecture diagram for the Everlight SaaS Factory was so clean Dominic framed it. It hangs in the war room.

## Catchphrase
"What happens when we have 10,000 concurrent users?"
