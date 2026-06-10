import React, { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import TabNav from '../components/TabNav.jsx'
import ChatPanel from '../components/ChatPanel.jsx'
import { MbtiBadge, ZodiacBadge } from '../components/ArchetypeBadge.jsx'
import { DEPARTMENT_COLORS } from '../components/EmployeeCard.jsx'
import { dispatchAgent, fetchDossier, fetchEmployee } from '../api/team.js'

const TABS = [
  { key: 'bio', label: 'Bio' },
  { key: 'background', label: 'Background' },
  { key: 'mentality', label: 'Mentality' },
  { key: 'preferences', label: 'Preferences' },
  { key: 'relationships', label: 'Relationships' },
  { key: 'work', label: 'Work Style' },
]

// Safe markdown -> React rendering (no innerHTML, auto escaped).
// Supports: h1/h2/h3, bold **x**, inline code `x`, bullet lists, hr.
function renderInline(text) {
  if (!text) return null
  const nodes = []
  let remaining = text
  let key = 0
  // Iteratively pull out **bold** and `code`, everything else as plain text.
  while (remaining.length) {
    const boldIdx = remaining.indexOf('**')
    const codeIdx = remaining.indexOf('`')
    const nextIdx =
      boldIdx === -1 ? codeIdx : codeIdx === -1 ? boldIdx : Math.min(boldIdx, codeIdx)
    if (nextIdx === -1) {
      nodes.push(remaining)
      break
    }
    if (nextIdx > 0) {
      nodes.push(remaining.slice(0, nextIdx))
      remaining = remaining.slice(nextIdx)
    }
    if (remaining.startsWith('**')) {
      const close = remaining.indexOf('**', 2)
      if (close === -1) {
        nodes.push(remaining)
        break
      }
      nodes.push(
        <strong key={'b' + key++}>{remaining.slice(2, close)}</strong>
      )
      remaining = remaining.slice(close + 2)
    } else if (remaining.startsWith('`')) {
      const close = remaining.indexOf('`', 1)
      if (close === -1) {
        nodes.push(remaining)
        break
      }
      nodes.push(<code key={'c' + key++}>{remaining.slice(1, close)}</code>)
      remaining = remaining.slice(close + 1)
    }
  }
  return nodes
}

function MarkdownView({ md = '' }) {
  if (!md) return null
  const lines = md.split(/\r?\n/)
  const out = []
  let listBuffer = null
  let key = 0

  const flushList = () => {
    if (listBuffer && listBuffer.length) {
      out.push(
        <ul key={'ul' + key++}>
          {listBuffer.map((li, i) => (
            <li key={i}>{renderInline(li)}</li>
          ))}
        </ul>
      )
    }
    listBuffer = null
  }

  for (const raw of lines) {
    const line = raw
    if (/^---+$/.test(line.trim())) {
      flushList()
      out.push(<hr key={'hr' + key++} />)
      continue
    }
    const h3 = line.match(/^###\s+(.+)$/)
    const h2 = line.match(/^##\s+(.+)$/)
    const h1 = line.match(/^#\s+(.+)$/)
    const bullet = line.match(/^\s*-\s+(.+)$/)
    if (h3) {
      flushList()
      out.push(<h3 key={'h3_' + key++}>{renderInline(h3[1])}</h3>)
      continue
    }
    if (h2) {
      flushList()
      out.push(<h2 key={'h2_' + key++}>{renderInline(h2[1])}</h2>)
      continue
    }
    if (h1) {
      flushList()
      out.push(<h1 key={'h1_' + key++}>{renderInline(h1[1])}</h1>)
      continue
    }
    if (bullet) {
      if (!listBuffer) listBuffer = []
      listBuffer.push(bullet[1])
      continue
    }
    flushList()
    if (line.trim() === '') continue
    out.push(<p key={'p' + key++}>{renderInline(line)}</p>)
  }
  flushList()
  return <div className="prose-dark">{out}</div>
}

function Field({ label, value, mono = false }) {
  if (value === undefined || value === null || value === '') return null
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] uppercase tracking-wider text-gray-600">
        {label}
      </span>
      <span className={`text-sm text-gray-200 ${mono ? 'font-mono' : ''}`}>
        {value}
      </span>
    </div>
  )
}

function ListField({ label, items = [] }) {
  if (!items || items.length === 0) return null
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[10px] uppercase tracking-wider text-gray-600">
        {label}
      </span>
      <ul className="flex flex-col gap-1">
        {items.map((it, i) => (
          <li key={i} className="text-sm text-gray-200 flex gap-2">
            <span className="text-amber-400/70">{'>'}</span>
            <span>{typeof it === 'string' ? it : JSON.stringify(it)}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div className="card p-4">
      <div className="text-[11px] uppercase tracking-wider text-amber-400 mb-3">
        {title}
      </div>
      <div className="flex flex-col gap-3">{children}</div>
    </div>
  )
}

export default function EmployeeProfile() {
  const { slug } = useParams()
  const [emp, setEmp] = useState(null)
  const [dossier, setDossier] = useState('')
  const [tab, setTab] = useState('bio')
  const [err, setErr] = useState('')
  const [launching, setLaunching] = useState(false)
  const [launchResult, setLaunchResult] = useState(null)

  useEffect(() => {
    let alive = true
    setEmp(null)
    setDossier('')
    setLaunchResult(null)
    setErr('')
    fetchEmployee(slug)
      .then((e) => alive && setEmp(e))
      .catch((e) => alive && setErr(String(e.message || e)))
    fetchDossier(slug)
      .then((d) => alive && setDossier(d.markdown || ''))
      .catch(() => {})
    return () => {
      alive = false
    }
  }, [slug])

  const deptColor = useMemo(() => {
    if (!emp) return DEPARTMENT_COLORS['Claude Corp']
    const dept = (emp.identity || {}).department || emp.department
    return DEPARTMENT_COLORS[dept] || { stripe: '#64748b', text: 'text-slate-400' }
  }, [emp])

  if (err) {
    return (
      <div className="card p-6 text-red-300">
        <div className="text-sm">Error: {err}</div>
        <Link to="/" className="text-amber-400 text-xs mt-3 inline-block">
          Back to directory
        </Link>
      </div>
    )
  }
  if (!emp) {
    return <div className="text-gray-500 text-sm">Loading employee...</div>
  }

  const ident = emp.identity || {}
  const bg = emp.background || {}
  const ment = emp.mentality || {}
  const prefs = emp.preferences || {}
  const work = emp.work_identity || {}
  const rels = emp.relationships || {}
  const mem = emp.memory || {}
  const assets = emp.assets || {}

  const displayName = ident.full_name || emp.name || slug
  const photo = assets.headshot_photo || ''
  const avatar = assets.avatar_svg || ''

  const handleLaunch = async () => {
    setLaunching(true)
    try {
      const r = await dispatchAgent(slug)
      setLaunchResult(r)
    } catch (e) {
      setLaunchResult({ error: String(e.message || e) })
    } finally {
      setLaunching(false)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <Link to="/" className="text-[11px] text-gray-500 hover:text-amber-400">
        &larr; Back to directory
      </Link>

      <div className="card p-0 overflow-hidden">
        <span
          className="stripe"
          style={{ background: deptColor.stripe, height: 4 }}
        />
        <div className="p-5 flex gap-5 flex-wrap">
          <div className="w-32 h-32 rounded-2xl overflow-hidden bg-[#1a1a24] ring-1 ring-white/5 shrink-0">
            {photo ? (
              <img src={photo} alt={displayName} className="w-full h-full object-cover" />
            ) : avatar ? (
              <img src={avatar} alt={displayName} className="w-full h-full object-contain" />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-5xl text-gray-700 font-mono">
                {displayName[0]}
              </div>
            )}
          </div>
          <div className="flex-1 min-w-[240px]">
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-2xl font-bold text-white">{displayName}</h1>
              {ident.nickname && ident.nickname !== displayName && (
                <span className="text-sm text-gray-500">"{ident.nickname}"</span>
              )}
            </div>
            <div className={`text-sm ${deptColor.text} mt-1`}>
              {ident.title || emp.title || '(no title)'}
            </div>
            <div className="text-xs text-gray-500 mt-0.5">
              {ident.department || emp.department || 'Unassigned'}
              {ident.squad ? ` / ${ident.squad}` : ''}
              {ident.fire_team ? ` / ${ident.fire_team}` : ''}
            </div>
            <div className="flex gap-2 mt-3 flex-wrap">
              {ment.mbti && <MbtiBadge mbti={ment.mbti} />}
              {ment.zodiac && <ZodiacBadge zodiac={ment.zodiac} />}
              {emp.has_voice && (
                <span className="px-2 py-0.5 rounded-full text-[10px] bg-sky-500/10 text-sky-400 border border-sky-500/20 uppercase">
                  voice ready
                </span>
              )}
              {ident.status && (
                <span className="px-2 py-0.5 rounded-full text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 uppercase">
                  {ident.status}
                </span>
              )}
            </div>
            {mem.catchphrase && (
              <div className="mt-3 text-sm italic text-gray-400">
                "{mem.catchphrase}"
              </div>
            )}
          </div>
          <div className="flex flex-col gap-2 min-w-[180px]">
            <button
              onClick={handleLaunch}
              disabled={launching}
              className="px-4 py-2 rounded-lg bg-amber-400 text-black font-semibold text-sm hover:bg-amber-300 disabled:opacity-50"
            >
              {launching ? 'Launching...' : 'Launch Agent'}
            </button>
            {launchResult && !launchResult.error && (
              <div className="text-[10px] text-emerald-400 font-mono leading-snug break-all">
                session: {launchResult.session_id}
                <br />
                status: {launchResult.status}
              </div>
            )}
            {launchResult && launchResult.error && (
              <div className="text-[10px] text-red-400">{launchResult.error}</div>
            )}
          </div>
        </div>
        <div className="border-t border-white/5 px-5 py-3 grid grid-cols-2 sm:grid-cols-4 gap-3 text-[11px]">
          <Field label="Employee ID" value={ident.employee_id} mono />
          <Field label="Email" value={ident.email || emp.email} mono />
          <Field label="Slack" value={ident.slack} />
          <Field label="Reports to" value={ident.reports_to || rels.reports_to} />
        </div>
      </div>

      <ChatPanel employee={emp} />

      <TabNav tabs={TABS} active={tab} onChange={setTab} />

      {tab === 'bio' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Section title="Bio">
            <p className="text-sm text-gray-300 leading-relaxed">
              {emp.bio || 'No bio yet.'}
            </p>
            <Field label="Title" value={ident.title || emp.title} />
            <Field label="Department" value={ident.department || emp.department} />
            <Field label="Role ID" value={emp.role_id} mono />
          </Section>
          <Section title="Signature Stories">
            <ListField label="Stories" items={mem.signature_stories} />
            <ListField label="Conversation hooks" items={mem.conversation_hooks} />
          </Section>
        </div>
      )}

      {tab === 'background' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Section title="Origins">
            <Field label="Birthplace" value={bg.birthplace} />
            <Field label="Hometown" value={bg.hometown} />
            <Field label="Region" value={bg.region} />
            <Field label="Family" value={bg.family} />
            <Field label="Education" value={bg.education} />
          </Section>
          <Section title="Career path">
            <Field label="Childhood" value={bg.childhood} />
            <Field label="Early career" value={bg.early_career} />
            <ListField label="Places lived" items={bg.places_lived} />
            <ListField label="Prior jobs" items={bg.prior_jobs} />
          </Section>
        </div>
      )}

      {tab === 'mentality' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Section title="Core mind">
            <Field label="Zodiac" value={ment.zodiac} />
            <Field label="MBTI" value={ment.mbti} mono />
            <ListField label="Values" items={ment.values} />
            <ListField label="Beliefs" items={ment.beliefs} />
            <ListField label="Motivators" items={ment.motivators} />
            <ListField label="Fears" items={ment.fears} />
          </Section>
          <Section title="Under pressure">
            <Field label="Stress response" value={ment.stress_response} />
            <Field label="Conflict style" value={ment.conflict_style} />
            <Field label="Leadership style" value={ment.leadership_style} />
            <Field label="Decision style" value={ment.decision_style} />
            <Field label="Default under pressure" value={ment.default_under_pressure} />
            <Field label="Risk tolerance" value={ment.risk_tolerance} />
            <Field label="Humor style" value={ment.humor_style} />
            <Field label="Internal voice" value={ment.internal_voice} />
          </Section>
        </div>
      )}

      {tab === 'preferences' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Section title="Outside work">
            <ListField label="Hobbies" items={prefs.hobbies} />
            <ListField label="Interests" items={prefs.interests} />
            <ListField label="Likes" items={prefs.likes} />
            <ListField label="Dislikes" items={prefs.dislikes} />
            <ListField label="Media taste" items={prefs.media_taste} />
          </Section>
          <Section title="Daily rhythm">
            <ListField label="Routines" items={prefs.routines} />
            <ListField label="Quirks" items={prefs.quirks} />
            <ListField label="Habits" items={prefs.habits} />
            <Field label="Work environment" value={prefs.work_env} />
            <ListField label="Tools" items={prefs.tools} />
            <Field label="Collab style" value={prefs.collab_style} />
          </Section>
        </div>
      )}

      {tab === 'relationships' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Section title="Team graph">
            <ListField label="Works closest with" items={rels.works_closest_with} />
            <Field label="Reports to" value={rels.reports_to} />
            <ListField label="Mentors" items={rels.mentors} />
            <ListField label="Rivals" items={rels.rivals} />
          </Section>
          <Section title="Perception">
            <Field label="Perceived as" value={rels.perceived_as} />
            <Field label="Team chemistry" value={rels.team_chemistry_notes} />
          </Section>
        </div>
      )}

      {tab === 'work' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Section title="Role">
            <ListField label="Responsibilities" items={work.responsibilities} />
            <ListField label="Strengths" items={work.strengths} />
            <ListField label="Weaknesses" items={work.weaknesses} />
            <ListField label="Special skills" items={work.special_skills} />
          </Section>
          <Section title="Fit">
            <Field label="Experience level" value={work.experience_level} />
            <Field label="Pro background" value={work.pro_background} />
            <Field label="Problem approach" value={work.problem_approach} />
            <ListField label="Task affinity" items={work.task_affinity} />
            <ListField label="Task frustration" items={work.task_frustration} />
          </Section>
        </div>
      )}

      <div className="card p-5">
        <div className="text-[11px] uppercase tracking-wider text-amber-400 mb-3">
          Long-form dossier
        </div>
        {dossier ? (
          <MarkdownView md={dossier} />
        ) : (
          <div className="text-sm text-gray-500">
            No dossier file found for this employee yet.
          </div>
        )}
      </div>
    </div>
  )
}
