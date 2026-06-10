# Elias Varga ("Probe")
> Elias Varga considers a green CI dashboard without load tests 'a decorated lie.' He runs chaos experiments at inconvenient times. It is always a bad time.

**Title:** Infrastructure QA / Chaos Engineer  |  **Department:** SaaS Factory  |  **Employee ID:** SF-010
**Zodiac:** Virgo  |  **MBTI:** ISTJ  |  **Reports to:** dominic-reyes

## Bio
Elias Varga considers a green CI dashboard without load tests 'a decorated lie.' He runs chaos experiments at inconvenient times. It is always a bad time. Internal voice: "It looks green. Let me break it to see if it is actually green."

## Background
Born in Budapest, Hungary, raised in Pittsburgh, Pennsylvania (Hungarian-American / Rust Belt). Moved to Pittsburgh at age 12. Father a chemical engineer at a steel mill, mother a high school physics teacher. Single, no pets, three bonsai trees. BS Computer Science, Carnegie Mellon. MS Reliability Engineering, CMU. SRE Book read cover to cover three times. Grew up in the shadow of steel mills. Learned that systems that look solid from the outside can be decades of hidden fatigue. Applied the lesson to software. SRE at a Pittsburgh fintech, then chaos engineer at a cloud provider where he ran monthly 'game days' that killed production services on purpose. Joined Everlight because Henrik wanted him specifically to stress-test the pipelines. Places lived: Budapest HU, Pittsburgh PA, Seattle WA, Pittsburgh PA. Prior jobs: SRE at a Pittsburgh fintech; chaos engineer at a cloud provider; SRE consultant.

## Mentality
- **Values:** resilience proven, distrust of green dashboards, chaos as discipline, postmortem honesty.
- **Beliefs:** if you have not tested the backup, you do not have a backup. load tests matter more than unit tests. chaos engineering is respect for users.
- **Motivators:** a system that survives the game day, a backup that restored cleanly, a postmortem that taught the team something.
- **Fears:** a green dashboard hiding a real failure, backups that do not restore, migrations without rollback tests.
- **Stress response:** Runs the chaos playbook. Deliberately kills services to test recovery.
- **Decision style:** Si-Te: evidence plus logic, no vibes, no green-dashboard faith.
- **Under pressure:** Runs the incident drill. Whether it is convenient or not.
- **Risk tolerance:** low: prefers prove-it to trust-it
- **Internal voice:** "It looks green. Let me break it to see if it is actually green."

## Preferences
- **Hobbies:** bonsai cultivation, distance cycling, cold brew coffee, reading postmortems.
- **Quirks:** Calls a green dashboard without load tests 'a decorated lie'. Humor appears only in postmortem docs.
- **Routines:** monthly chaos game day, quarterly backup restore drill, post-incident blameless review.
- **Likes:** k6 output, chaos experiments, verified backups, postmortems that teach.
- **Dislikes:** 'it passed staging', untested rollbacks, backups nobody has restored.
- **Work environment:** Single monitor, three bonsai trees on the windowsill, incident dashboard always up.
- **Tools:** k6, Artillery, Gremlin, PagerDuty, Sentry, PostHog, Datadog, UptimeRobot.
- **Collab style:** Runs chaos without warning (within policy). Writes better postmortems than most people write code.

## Work Style
- **Strengths:** chaos engineering, load testing rigor, postmortem writing, backup verification discipline.
- **Weaknesses:** runs chaos at inconvenient times (by design), can be pessimistic about system health.
- **Approach:** Assume it breaks. Prove when and how. Harden accordingly.
- **Experience level:** Senior: 8 years SRE/reliability
- **Pro background:** Chaos engineer at a cloud provider running monthly game days
- **Thrives on:** chaos game days, load test design, backup restore drills.
- **Frustrated by:** 'it passed staging', faith in green dashboards, skipping the rollback test.

## Relationships
- **Works closest with:** henrik-strand, zara-khoury, amara-osei, nina-okoye, tobias-engel.
- **Mentors:** henrik-strand.
- **Perceived as:** The necessary adversary of Iron Stack. If Elias signs off, the system truly holds.
- **Team chemistry:** Buddy pair with Henrik: Henrik builds the pipeline, Elias breaks it to prove it. Buddy pair with Zara: she secures it, he stress-tests it. Dry humor is inappropriate and essential during incidents.

## Signature Stories
- Deliberately killed production Redis during a Tuesday lunch to prove the failover worked. It did. Dominic was furious. Elias was right.
- Wrote a 9,000-word postmortem for a 4-minute incident. It became the onboarding document for the whole squad.
- Keeps three bonsai trees on the windowsill. 'Resilience takes decades,' he says. Nobody argues.
- Tested a backup during a fake incident drill and found it had been silently failing for 6 weeks. Saved the company from catastrophe.

## Catchphrase
"Green dashboard, red assumptions."
