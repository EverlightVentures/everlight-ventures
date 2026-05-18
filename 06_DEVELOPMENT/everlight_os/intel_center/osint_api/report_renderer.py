"""
report_renderer -- branded HTML profile report.

Pure function. Takes:
  - profile  (from profile_synthesizer.synthesize)
  - state_rules (from legal_state.state_rules_for, or None)
  - watermark dict {viewer, ts}

Returns a single HTML string with:
  - Gold-on-dark Everlight palette (Playfair + Inter + JetBrains Mono)
  - Diagonal "INTERNAL" watermark + per-view watermark top-right
  - Per-state legal panel (channels matrix, restrictions, citations) at the top
  - Hero card (subject, kind, DNC banner if present)
  - KPI strip (findings counts + confidence breakdown)
  - Section cards: Risk -> Contact -> Online -> Property -> Business
  - Each finding: confidence chip, "View source ->" link, investigator attribution
  - Sources Run footer (per-investigator timing + counts)
  - Universal legal footer (FCRA + GLBA + business_purpose + INTERNAL warning)
"""
from __future__ import annotations

import html as _html
from datetime import datetime


def _esc(s) -> str:
    return _html.escape(str(s) if s is not None else "")


def _conf_chip(conf, signals=None):
    if conf is None:
        return ""
    cls = "conf-low"
    if conf >= 70: cls = "conf-high"
    elif conf >= 50: cls = "conf-med"
    title = "; ".join(signals or []) if signals else "no signals matched"
    return f'<span class="conf-chip {cls}" title="{_esc(title)}">conf {int(conf)}</span>'


def _section_html(title, items, accent_color, icon_emoji):
    if not items:
        return ""
    rows = []
    for f in items:
        conf = _conf_chip(f.get("confidence"), f.get("matched_signals"))
        url = f.get("url", "")
        url_link = (f'<a class="src-link" href="{_esc(url)}" target="_blank" rel="noopener">View source →</a>'
                    if url else '')
        inv = f.get("investigator", "")
        rows.append(f"""
        <div class="finding">
          <div class="finding-head">
            <span class="chip chip-gold">{_esc(f.get("label",""))}</span>
            {conf}
            <span class="finding-attribution">{_esc(inv)}</span>
          </div>
          <div class="finding-value">{_esc(f.get("value",""))}</div>
          <div class="finding-actions">
            {url_link}
          </div>
        </div>""")
    return f"""
    <section class="section" style="--accent:{accent_color}">
      <div class="section-head">
        <span class="section-icon">{icon_emoji}</span>
        <h2>{_esc(title)}</h2>
        <span class="section-count">{len(items)}</span>
      </div>
      <div class="section-body">
        {''.join(rows)}
      </div>
    </section>"""


def _state_legal_panel(state_rules):
    if not state_rules:
        return ""
    state = _esc(state_rules.get("state", "?"))
    name = _esc(state_rules.get("name", state))

    # Channel matrix
    channels = state_rules.get("channels_allowed", {})
    channel_rows = []
    for ch in ["email", "sms", "call", "mail", "preforeclosure_outreach", "autonomous_bot_call"]:
        if ch not in channels:
            continue
        v = channels[ch]
        if v is True:
            color, label = "#22c55e", "ALLOWED"
        elif v is False:
            color, label = "#dc2626", "BLOCKED"
        else:
            color, label = "#c9a84c", str(v).upper().replace("_", " ")
        channel_rows.append(f"""
        <tr>
          <td>{_esc(ch.replace('_', ' ').title())}</td>
          <td><span class="status-chip" style="background:{color}22; color:{color}; border-color:{color}66;">{label}</span></td>
        </tr>""")

    restrictions = state_rules.get("active_restrictions", [])
    restr_html = ""
    if restrictions:
        restr_list = "".join(
            f'<li><strong>{_esc(r.get("statute",""))}:</strong> {_esc(r.get("summary",""))}</li>'
            for r in restrictions
        )
        restr_html = f"""
        <div class="restrictions-block">
          <div class="block-title">⚠ Active restrictions for {state}</div>
          <ul>{restr_list}</ul>
        </div>"""

    warning = state_rules.get("warning", "")
    warning_html = ""
    if warning and not state_rules.get("covered"):
        warning_html = f"""
        <div class="hard-block-banner">
          <span class="hard-block-icon">⛔</span>
          <div>
            <div class="hard-block-title">UNKNOWN STATE</div>
            <div class="hard-block-detail">{_esc(warning)}</div>
          </div>
        </div>"""
    elif warning:
        warning_html = f"""
        <div class="hard-block-banner">
          <span class="hard-block-icon">⛔</span>
          <div>
            <div class="hard-block-title">HARD BLOCK · {state}</div>
            <div class="hard-block-detail">{_esc(warning)}</div>
          </div>
        </div>"""

    citations = state_rules.get("citations", [])
    cit_html = ""
    if citations:
        cit_html = "<div class='citations'>Citations: " + ", ".join(_esc(c) for c in citations) + "</div>"

    wholesale_status = _esc(state_rules.get("wholesale_legal_status", "unknown"))

    return f"""
    <section class="state-legal-panel">
      <div class="legal-panel-head">
        <div>
          <div class="panel-eyebrow">PER-STATE COMPLIANCE</div>
          <h2 class="panel-title">{name} ({state}) <span class="panel-sub">— wholesale: {wholesale_status}</span></h2>
        </div>
        <div class="panel-stamp">verified per Everlight state_gates.json</div>
      </div>

      {warning_html}

      <div class="legal-panel-grid">
        <div>
          <div class="block-title">Channel matrix</div>
          <table class="channel-table">
            <thead><tr><th>Channel</th><th>Status</th></tr></thead>
            <tbody>{''.join(channel_rows)}</tbody>
          </table>
        </div>
        <div>
          {restr_html if restrictions else '<div class="block-title">Active restrictions</div><div class="empty-state">None known for ' + state + ' (still subject to federal TCPA + CAN-SPAM)</div>'}
        </div>
      </div>

      {cit_html}
    </section>"""


def render_profile_html(profile: dict, state_rules: dict | None = None,
                         watermark: dict | None = None,
                         business_purpose: str = "") -> str:
    """The core function. Pure HTML, no I/O."""
    if not isinstance(profile, dict):
        profile = {}
    if not isinstance(watermark, dict):
        watermark = {}

    # Re-compute TLDR with state_rules so action lines are right
    try:
        from .profile_synthesizer import _build_tldr
        profile["tldr"] = _build_tldr(
            profile.get("target", ""), profile.get("kind", ""),
            profile.get("sections", {}), profile.get("stats", {}),
            profile.get("verification_summary", {}),
            bool(profile.get("dnc_blocked")),
            state_rules,
        )
    except Exception:
        pass

    target = _esc(profile.get("target", "(unknown)"))
    kind = _esc(profile.get("kind", "unknown"))
    inv_id = _esc(profile.get("investigation_id", ""))
    started_at = _esc(profile.get("started_at", "")[:19])
    elapsed_ms = profile.get("elapsed_ms", 0)
    triggered_by = _esc(profile.get("triggered_by", "unknown"))
    stats = profile.get("stats", {})
    sections = profile.get("sections", {})
    sources_run = profile.get("sources_run", [])
    dnc_blocked = profile.get("dnc_blocked", False)
    dnc_reason = _esc(profile.get("dnc_reason", ""))
    viewer = _esc(watermark.get("viewer", "Everlight Operator"))
    view_ts = _esc(watermark.get("ts", datetime.now().isoformat()[:19]))

    # KPI strip
    kpi_rows = [
        ("Verified", stats.get("verified_findings", 0), "#22c55e"),
        ("High conf (≥70)", stats.get("high_confidence", 0), "#22c55e"),
        ("Total raw findings", stats.get("total_findings", 0), "#c9a84c"),
        ("Filtered (junk)", stats.get("garbage_filtered", 0), "#dc2626"),
        ("Sources w/ data", f"{stats.get('sources_returning_data', 0)} / {stats.get('investigators_run', 0)}", "#8b5cf6"),
        ("Elapsed", f"{int(elapsed_ms/1000)}s" if elapsed_ms > 1000 else f"{elapsed_ms}ms", "#22d3ee"),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><div class="kpi-label">{_esc(label)}</div>'
        f'<div class="kpi-value" style="color:{color}">{_esc(value)}</div></div>'
        for label, value, color in kpi_rows
    )

    # DNC banner
    dnc_html = ""
    if dnc_blocked:
        dnc_html = f"""
        <div class="dnc-banner">
          <span class="dnc-icon">⛔</span>
          <div>
            <div class="dnc-title">DNC BLOCKED · DO NOT CONTACT</div>
            <div class="dnc-detail">{dnc_reason or 'On Everlight DNC list'}. NO outreach permitted on any channel.</div>
          </div>
        </div>"""

    # Sections
    sec_html = (
        _section_html("Risk Signals", sections.get("risk", []), "#dc2626", "⚠") +
        _section_html("Contact", sections.get("contact", []), "#c9a84c", "✉") +
        _section_html("Online Presence", sections.get("online", []), "#22d3ee", "🌐") +
        _section_html("Property", sections.get("property", []), "#22c55e", "🏠") +
        _section_html("Business", sections.get("business", []), "#8b5cf6", "🏛") +
        _section_html("Additional Research Sources", sections.get("research", []), "#c9a84c", "📚")
    )
    if not sec_html.strip():
        sec_html = '<div class="empty-state-large">No verified findings. Try investigating with more lead context (state, city, email) to improve confidence.</div>'

    # Sources Run
    src_rows = []
    for s in sources_run:
        ok_chip = '<span class="status-chip" style="background:#22c55e22;color:#22c55e">OK</span>' if s.get("ok") else '<span class="status-chip" style="background:#dc262622;color:#dc2626">FAIL</span>'
        src_rows.append(f"""
        <tr>
          <td>{_esc(s.get('name', s.get('id', '?')))}</td>
          <td>{ok_chip}</td>
          <td class="num">{s.get('verified_count', 0)} / {s.get('raw_count', 0)}</td>
          <td class="num">{s.get('elapsed_ms', 0)}ms</td>
          <td class="dim">{_esc(s.get('error', ''))}</td>
        </tr>""")

    # Legal footer -- per Brief Calloway 2026-05-12 audit (FCRA subsections,
    # GLBA cites, CCPA, GDPR, defamation safe-harbor, DTSA trade-secret designation)
    legal_html = f"""
    <section class="legal-footer">
      <h3>Legal disclaimers</h3>

      <div class="legal-block">
        <strong>Fair Credit Reporting Act (FCRA):</strong> This report is NOT a consumer report
        as defined at 15 U.S.C. §§ 1681a(d), 1681b. It may not be used for any "permissible
        purpose" enumerated under § 1681b (credit, employment, insurance, housing tenancy,
        government benefits, court-ordered child support, or other FCRA-regulated decisions).
        The adverse-action duties of § 1681m do not attach because no consumer report is involved.
        Findings are derived from publicly available sources and may be inaccurate, incomplete,
        outdated, or pertain to a different individual sharing the same name (a "name collision").
      </div>

      <div class="legal-block">
        <strong>Gramm-Leach-Bliley Act (GLBA):</strong> All financial information referenced is
        from publicly available sources for which Everlight Ventures has a permissible business
        purpose. No nonpublic personal information was obtained from a financial institution by
        pretext or false statement in violation of 15 U.S.C. §§ 6801-6809 (privacy) or
        §§ 6821-6827 (pretexting / fraudulent access).
      </div>

      <div class="legal-block">
        <strong>California Consumer Privacy Act / CPRA:</strong> If the subject of this report
        is a California resident, they have the right to know what personal information
        Everlight Ventures has collected (Cal. Civ. Code § 1798.100), to request deletion
        (§ 1798.105), and to opt out of "sale" or "sharing" (§ 1798.120). Requests:
        <code>privacy@everlightventures.io</code>. This report is created for the "business
        purpose" defined at § 1798.140(e); no data is sold or shared with third parties.
      </div>

      <div class="legal-block">
        <strong>GDPR (if applicable):</strong> Where the subject is an identified or
        identifiable EU/UK natural person, Everlight relies on Article 6(1)(f) GDPR
        (legitimate interests) as the lawful basis for this limited business-intelligence
        processing, subject to the subject's right to object under Article 21.
      </div>

      <div class="legal-block">
        <strong>Opinion + qualified common-interest privilege:</strong> All synthesized
        characterizations in this report are statements of opinion based on cited public
        sources, made under the qualified common-interest privilege among authorized Everlight
        Ventures personnel for a legitimate business purpose. No third-party republication is
        authorized. Distribution outside the authorized recipient list waives the privilege.
      </div>

      <div class="legal-block">
        <strong>Permissible business purpose</strong> stated for this investigation:
        <em class="quote">"{_esc(business_purpose) or '(not provided)'}"</em>
      </div>

      <div class="legal-block">
        <strong>State-specific compliance</strong> rules consulted are shown in the panel above
        and sourced from <code>Wholesale/compliance/state_gates.json</code>. Per-state hard
        blocks (TX SB 140, CA Civ. Code §§ 2945/1695, NC HB 797, FL FTSA, OH ORC §1349.61,
        IL HB 1535, MO No-Call) are enforced before any contact is recommended. Where the
        target's state is unknown, every channel is treated as blocked until verified.
      </div>

      <div class="legal-block">
        <strong>Source scope:</strong> public social profiles, public consumer reviews (Yelp,
        Goodreads, Strava, Untappd, Letterboxd, etc.), civic + court records, public
        philanthropy (FEC/990s), news + obit archives, property assessor records, and
        professional license lookups. <em>Excluded</em>: HIPAA-protected medical records,
        DMV data (DPPA 18 USC §2721), consumer credit (FCRA), nonpublic financial info
        (GLBA §§6801-6809), private communications (ECPA §§2510-2522), private support-group
        membership, and any records about minors. See <code>osint_api/legal_scope.py</code>.
      </div>

      <div class="legal-block warning-block">
        <strong>INTERNAL USE ONLY · TRADE SECRET</strong> -- This report and its synthesis
        constitute Everlight Ventures trade secret information under the Defend Trade Secrets
        Act, 18 U.S.C. §§ 1836, 1839. DO NOT DISTRIBUTE outside Everlight Ventures authorized
        personnel. The operator is responsible for verifying any finding before acting. Per
        Operator Truth doctrine: unverified data is integrity-grade failure.
      </div>
    </section>"""

    state_panel_html = _state_legal_panel(state_rules) if state_rules else ""

    # ============== PROFILE DEPTH SCORE ==============
    depth = profile.get("depth") or {}
    depth_html = ""
    if depth:
        score_n = depth.get("overall_score", 0)
        verdict = depth.get("verdict", "")
        score_color = "#22c55e" if score_n >= 75 else ("#c9a84c" if score_n >= 55 else "#dc2626")
        breakdown = depth.get("breakdown", {})
        recs = depth.get("recommendations", [])
        breakdown_rows = "".join(
            f"""<div class="depth-axis">
              <div class="depth-axis-label">{_esc(k.replace('_',' ').title())}</div>
              <div class="depth-axis-bar"><span style="width:{v}%; background:{('#22c55e' if v>=75 else ('#c9a84c' if v>=40 else '#dc2626'))}"></span></div>
              <div class="depth-axis-score">{v}</div>
            </div>"""
            for k, v in sorted(breakdown.items(), key=lambda x: -x[1])
        )
        rec_rows = "".join(
            f"""<div class="rec-row">
              <div class="rec-axis">{_esc(r.get('axis','').replace('_',' '))}</div>
              <div class="rec-text">{_esc(r.get('next_step',''))}</div>
            </div>"""
            for r in recs
        )
        depth_html = f"""
        <section class="depth-card">
          <div class="depth-eyebrow">★ Profile Depth</div>
          <div class="depth-score-row">
            <div class="depth-score" style="color:{score_color}">{score_n}<span class="depth-score-suffix">/100</span></div>
            <div class="depth-verdict">{_esc(verdict)}</div>
          </div>
          <div class="depth-grid">
            <div>
              <div class="p-label">DIMENSIONS</div>
              <div class="depth-axes">{breakdown_rows}</div>
            </div>
            <div>
              <div class="p-label">RECOMMENDED NEXT STEPS</div>
              {rec_rows or '<div class="p-empty">All major axes scored above 50.</div>'}
            </div>
          </div>
        </section>"""

    # ============== PITCH PACKAGE (5-stage pipeline) ==============
    pkg = profile.get("pitch_package") or {}
    pkg_html = ""
    if pkg and pkg.get("stage4_narrative", {}).get("touchpoints"):
        narrative = pkg["stage4_narrative"]
        strategy = pkg.get("stage3_strategy", {})
        resonance = pkg.get("stage2_resonance", {})
        routing = pkg.get("stage5_routing", {})

        # Resonance / values chips
        value_chips = "".join(
            f'<span class="pchip pchip-cyan">{_esc(v)}</span>'
            for v in resonance.get("values", [])[:6]
        )
        sens_chips = "".join(
            f'<span class="pchip pchip-red">{_esc(s.replace("_"," "))}</span>'
            for s in resonance.get("sensitivities", [])
        )
        angle_rows = "".join(
            f"""<div class="angle-row">
              <span class="pchip pchip-gold">{_esc(a.get('value',''))}</span>
              <div class="angle-text">{_esc(a.get('angle',''))}</div>
            </div>"""
            for a in strategy.get("positioning_angles", [])
        )

        # Touchpoints
        tp_rows = ""
        for tp in narrative.get("touchpoints", []):
            channels_html = ""
            for ch_name, ch in (tp.get("channel_copy") or {}).items():
                if ch_name == "email":
                    body = ch.get("body", "").replace("\n", "<br>")
                    channels_html += f"""
                    <div class="ch-block">
                      <div class="ch-label">EMAIL · subject: <em>{_esc(ch.get('subject',''))}</em></div>
                      <div class="ch-body">{body}</div>
                    </div>"""
                elif ch_name == "sms":
                    channels_html += f"""
                    <div class="ch-block">
                      <div class="ch-label">SMS</div>
                      <div class="ch-body ch-mono">{_esc(ch.get('body',''))}</div>
                    </div>"""
                elif ch_name == "voicemail":
                    channels_html += f"""
                    <div class="ch-block">
                      <div class="ch-label">VOICEMAIL SCRIPT</div>
                      <div class="ch-body ch-mono">{_esc(ch.get('script',''))}</div>
                    </div>"""
                elif ch_name == "mail":
                    body = ch.get("body", "").replace("\n", "<br>")
                    channels_html += f"""
                    <div class="ch-block">
                      <div class="ch-label">DIRECT MAIL (long-form letter)</div>
                      <div class="ch-body">{body}</div>
                    </div>"""
            tp_rows += f"""
            <div class="touchpoint">
              <div class="tp-head">
                <span class="tp-step">Touch {tp.get('step','?')}</span>
                <span class="tp-name">{_esc(tp.get('name','').upper())}</span>
                <span class="tp-when">send +{tp.get('send_after_days',0)}d</span>
              </div>
              <div class="tp-rationale">{_esc(tp.get('rationale',''))}</div>
              {channels_html}
            </div>"""

        # Routing chain
        route_rows = "".join(
            f'<div class="route-step">{_esc(s)}</div>'
            for s in routing.get("state_routing_chain", [])
        )

        pkg_html = f"""
        <section class="pkg-card">
          <div class="pkg-eyebrow">★ Pitch Package -- Multi-Touchpoint Story</div>

          <div class="pkg-stage">
            <div class="pkg-stage-label">Stage 2 · Resonance</div>
            <div class="pkg-stage-body">
              <div class="pkg-row"><span class="pkg-row-label">Tone</span><span class="pchip pchip-gold">{_esc(resonance.get('tone',''))}</span></div>
              <div class="pkg-row"><span class="pkg-row-label">Values</span>{value_chips or '<span class="p-empty">none derived</span>'}</div>
              {f'<div class="pkg-row"><span class="pkg-row-label">Sensitivities</span>{sens_chips}</div>' if sens_chips else ''}
            </div>
          </div>

          <div class="pkg-stage">
            <div class="pkg-stage-label">Stage 3 · Positioning Angles (woven implicitly into copy)</div>
            <div class="pkg-stage-body">{angle_rows or '<div class="p-empty">No angles derived</div>'}</div>
          </div>

          <div class="pkg-stage">
            <div class="pkg-stage-label">Stage 4 · Narrative -- {len(narrative.get('touchpoints',[]))} Touchpoints</div>
            <div class="pkg-stage-body">{tp_rows}</div>
          </div>

          <div class="pkg-stage">
            <div class="pkg-stage-label">Stage 5 · Routing</div>
            <div class="pkg-stage-body">
              <div class="route-primary">Primary closer: <strong>{_esc(routing.get('primary_closer_agent','?'))}</strong>{' · COMPLIANCE GATE REQUIRED' if routing.get('compliance_check_required') else ''}</div>
              {route_rows}
            </div>
          </div>

          <div class="pkg-footer">
            Per operator doctrine: this pitch RESONATES with the value-set inferred from
            findings -- it never CITES the source. The recipient sees recognition, not
            surveillance. DNC + state-channel rules ALWAYS override this package.
          </div>
        </section>"""

    # ============== PERSONALIZATION + PITCH HOOKS ==============
    personality = profile.get("personality") or {}
    pitch_hooks_list = profile.get("pitch_hooks") or []
    personalization_html = ""
    if personality and not personality.get("error"):
        interests = personality.get("interests") or {}
        life_events = personality.get("life_events") or {}
        fin = personality.get("financial_signals") or []
        red = personality.get("red_flags") or []
        prof_hits = personality.get("profession") or []
        comm = personality.get("communication_style", "neutral")

        # Interest chips
        interest_chips = ""
        for cat, hits in interests.items():
            kws = ", ".join(h["keyword"] for h in hits[:3])
            interest_chips += f'<span class="pchip pchip-gold" title="{_esc(kws)}">{_esc(cat)}</span>'

        # Life event chips
        life_chips = ""
        for tag in life_events:
            life_chips += f'<span class="pchip pchip-red">{_esc(tag.replace("_", " "))}</span>'

        # Profession line
        prof_line = ""
        if prof_hits:
            prof_line = "; ".join(p.get("value", "")[:80] for p in prof_hits[:2])

        # Financial signals line
        fin_chips = ""
        for f in fin:
            fin_chips += f'<span class="pchip pchip-orange">{_esc(f.get("kind","").replace("_"," "))}</span>'

        # Red flag line
        red_chips = ""
        for r in red[:3]:
            red_chips += f'<span class="pchip pchip-red">red flag</span>'

        # Pitch hooks block
        hook_rows = ""
        for h in pitch_hooks_list[:5]:
            cat_color = {"life_event":"red", "financial":"orange",
                          "interest":"gold", "generic":"dim"}.get(h.get("category"), "gold")
            hook_rows += f"""
            <div class="hook-row">
              <div class="hook-cat-pill pchip-{cat_color}">{_esc(h.get("category","").replace("_"," "))}</div>
              <div class="hook-body">
                <div class="hook-text">{_esc(h.get("hook",""))}</div>
                <div class="hook-rationale">
                  <span class="hook-rationale-label">Why this works:</span> {_esc(h.get("rationale",""))}
                </div>
              </div>
            </div>"""

        personalization_html = f"""
        <section class="personalization-card">
          <div class="personalization-eyebrow">★ Personalization & Pitch Hooks</div>
          <div class="personalization-grid">
            <div class="p-block">
              <div class="p-label">INTERESTS DETECTED</div>
              <div class="p-chips">{interest_chips or '<span class="p-empty">No interests detected (re-run with more lead context)</span>'}</div>
            </div>
            <div class="p-block">
              <div class="p-label">LIFE EVENTS</div>
              <div class="p-chips">{life_chips or '<span class="p-empty">None detected</span>'}</div>
            </div>
            <div class="p-block">
              <div class="p-label">PROFESSION / ROLE</div>
              <div class="p-text">{_esc(prof_line) or '<span class="p-empty">Not detected</span>'}</div>
            </div>
            <div class="p-block">
              <div class="p-label">SIGNALS</div>
              <div class="p-chips">{fin_chips}{red_chips}<span class="pchip pchip-{'gold' if comm=='formal' else ('cyan' if comm=='casual' else 'dim')}">style: {comm}</span></div>
            </div>
          </div>

          <div class="hooks-section">
            <div class="p-label" style="margin-bottom:14px;">RECOMMENDED PITCH HOOKS</div>
            {hook_rows or '<div class="p-empty">Not enough signals -- use generic foreclosure-relief opener.</div>'}
          </div>

          <div class="personalization-footer">
            Every signal cites its source ("Why this works" line). Verify before sending.
            These hooks are pattern-matched from public findings -- they're SUGGESTIONS, not psychology readings.
            DNC + state-channel rules ALWAYS override these hooks.
          </div>
        </section>"""

    # TLDR Summary card -- the part the operator actually reads
    tldr = profile.get("tldr") or {}
    tldr_html = ""
    if tldr:
        action_items_html = "".join(
            f'<li>{_esc(line)}</li>' for line in tldr.get("action_lines", [])
        )
        tldr_html = f"""
        <section class="tldr-card">
          <div class="tldr-eyebrow">★ At a glance</div>
          <div class="tldr-grid">
            <div class="tldr-block">
              <div class="tldr-label">WHO</div>
              <div class="tldr-text">{_esc(tldr.get("who",""))}</div>
            </div>
            <div class="tldr-block">
              <div class="tldr-label">WHAT WE FOUND</div>
              <div class="tldr-text">{_esc(tldr.get("what_found",""))}</div>
            </div>
            <div class="tldr-block tldr-block-trust">
              <div class="tldr-label">CAN YOU TRUST IT?</div>
              <div class="tldr-text">{_esc(tldr.get("trust",""))}</div>
            </div>
            {f'<div class="tldr-block tldr-block-action"><div class="tldr-label">WHAT YOU CAN DO</div><ul class="tldr-actions">{action_items_html}</ul></div>' if action_items_html else ''}
          </div>
        </section>"""

    # Garbage findings collapsible
    garbage_findings = profile.get("garbage_findings", [])
    garbage_html = ""
    if garbage_findings:
        gar_rows = []
        for f in garbage_findings:
            reason = f.get("garbage_reason", "")
            reason_label = {
                "auth_gated": "🔒 needs login",
                "dead_link": "✗ dead link",
                "raw_json_dump": "📄 raw JSON",
                "irrelevant_archive_item": "📚 unrelated archive",
                "manual_lookup_only": "🔎 manual search",
            }.get(reason, "")
            if not reason_label and reason.startswith("unverified_conf_"):
                conf_val = reason.replace("unverified_conf_", "")
                reason_label = f"❓ unverified (conf {conf_val})"
            elif not reason_label:
                reason_label = reason or "low signal"
            url = f.get("humanized_url") or f.get("url", "")
            url_label = f.get("humanized_label") or "open"
            link_html = f'<a class="src-link" href="{_esc(url)}" target="_blank" rel="noopener">{_esc(url_label)} →</a>' if url else ""
            gar_rows.append(f"""
            <div class="garbage-row">
              <span class="garbage-reason">{reason_label}</span>
              <span class="garbage-label">{_esc(f.get('label',''))}</span>
              <span class="garbage-value">{_esc(f.get('value',''))[:120]}</span>
              {link_html}
              <span class="garbage-investigator">{_esc(f.get('investigator',''))}</span>
            </div>""")
        garbage_html = f"""
        <details class="garbage-section">
          <summary><span class="garbage-summary-icon">🗑</span> {len(garbage_findings)} findings auto-filtered as low-value (auth-gated, dead links, raw JSON dumps, unrelated archive items)</summary>
          <div class="garbage-body">{''.join(gar_rows)}</div>
        </details>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#0a0a0f">
<meta http-equiv="Cache-Control" content="no-store">
<title>Profile Report · {target} · Intel Center</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {{
    --gold:#c9a84c; --gold-glow:#e0c66a; --bg:#0a0a0f; --panel:#15140f; --line:#2a2615;
    --text:#e8e8e8; --dim:#999;
    --green:#22c55e; --red:#dc2626; --cyan:#22d3ee; --purple:#8b5cf6; --orange:#f97316;
  }}
  *{{ box-sizing:border-box; }}
  body {{
    background: var(--bg); color: var(--text); font-family: Inter, sans-serif;
    line-height: 1.55; margin: 0; min-height: 100vh; position: relative; overflow-x: hidden;
  }}
  /* Diagonal repeating INTERNAL watermark */
  body::before {{
    content: '';
    position: fixed; inset: 0; pointer-events: none; z-index: 1;
    background-image: repeating-linear-gradient(
      -25deg,
      transparent 0px, transparent 200px,
      rgba(220, 38, 38, 0.04) 200px, rgba(220, 38, 38, 0.04) 220px
    );
  }}
  body::after {{
    content: 'INTERNAL · EVERLIGHT VENTURES · INTERNAL · EVERLIGHT VENTURES · INTERNAL · EVERLIGHT VENTURES · INTERNAL · EVERLIGHT VENTURES';
    position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%) rotate(-25deg);
    font-family: 'JetBrains Mono', monospace; font-size: 12rem; font-weight: 900;
    color: rgba(220, 38, 38, 0.025); white-space: nowrap; letter-spacing: 1rem;
    pointer-events: none; z-index: 1; user-select: none;
  }}
  .mesh {{ position: fixed; inset: 0; pointer-events: none; z-index: 0; overflow: hidden; opacity: .5; }}
  .mesh::before, .mesh::after {{ content: ''; position: absolute; border-radius: 50%; filter: blur(80px); opacity: .45; }}
  .mesh::before {{ width: 520px; height: 520px; left: -10%; top: -15%; background: radial-gradient(closest-side, #3a2a08, transparent); }}
  .mesh::after {{ width: 480px; height: 480px; right: -8%; top: 35%; background: radial-gradient(closest-side, #2a1135, transparent); }}

  /* Top-right viewer watermark */
  .view-stamp {{
    position: fixed; top: 14px; right: 18px; z-index: 100;
    background: rgba(220, 38, 38, 0.12); border: 1px solid rgba(220, 38, 38, 0.4);
    color: #f87171; font-family: 'JetBrains Mono', monospace; font-size: .65rem;
    padding: .35rem .75rem; border-radius: 9999px; letter-spacing: .08em;
  }}

  header {{
    border-bottom: 2px solid var(--gold);
    padding: 48px 56px 32px;
    background: radial-gradient(ellipse at top, rgba(201,168,76,0.08), transparent 60%), var(--bg);
    position: relative; z-index: 2;
  }}
  .wordmark {{ font-family: 'Playfair Display', serif; font-weight: 900; color: var(--gold); letter-spacing: .15em; font-size: .85rem; text-transform: uppercase; }}
  h1 {{ font-family: 'Playfair Display', serif; font-weight: 700; color: var(--gold); margin: 8px 0 4px; font-size: 2.4rem; text-shadow: 0 0 24px rgba(201,168,76,.45); }}
  .header-meta {{ color: var(--dim); font-size: .9rem; margin-top: 4px; font-family: 'JetBrains Mono', monospace; }}
  .header-meta .gold {{ color: var(--gold); }}
  .kind-chip {{
    display: inline-block; padding: .2rem .7rem; border-radius: 9999px;
    background: rgba(139,92,246,.1); color: #a78bfa; border: 1px solid rgba(139,92,246,.4);
    font-family: 'JetBrains Mono', monospace; font-size: .7rem; letter-spacing: .08em; margin-left: 12px;
  }}

  main {{ padding: 32px 56px 80px; max-width: 1200px; margin: 0 auto; position: relative; z-index: 2; }}

  /* DNC banner */
  .dnc-banner {{
    display: flex; gap: 14px; align-items: center;
    background: rgba(220,38,38,0.15); border: 2px solid rgba(220,38,38,0.6);
    border-radius: 12px; padding: 18px 22px; margin-bottom: 28px;
  }}
  .dnc-icon {{ font-size: 2rem; }}
  .dnc-title {{ color: #fca5a5; font-weight: 700; font-size: 1.05rem; letter-spacing: .05em; }}
  .dnc-detail {{ color: #fee2e2; font-size: .85rem; margin-top: 4px; }}

  /* Per-state legal panel */
  .state-legal-panel {{
    background: linear-gradient(135deg, rgba(201,168,76,0.10), rgba(201,168,76,0.02));
    border: 1px solid rgba(201,168,76,0.35); border-radius: 14px; padding: 28px; margin-bottom: 28px;
  }}
  .legal-panel-head {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }}
  .panel-eyebrow {{ font-size: .7rem; text-transform: uppercase; letter-spacing: .2em; color: var(--gold); font-weight: 600; }}
  .panel-title {{ font-family: 'Playfair Display', serif; color: var(--gold); margin: 6px 0; font-size: 1.6rem; }}
  .panel-sub {{ color: var(--dim); font-size: .9rem; font-weight: 400; }}
  .panel-stamp {{ font-family: 'JetBrains Mono', monospace; font-size: .65rem; color: var(--dim); letter-spacing: .08em; }}
  .legal-panel-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 16px; }}
  .block-title {{ font-size: .75rem; text-transform: uppercase; letter-spacing: .12em; color: var(--gold); margin-bottom: 8px; font-weight: 600; }}
  .channel-table {{ width: 100%; border-collapse: collapse; font-size: .85rem; }}
  .channel-table th, .channel-table td {{ padding: 6px 10px; border-bottom: 1px solid rgba(255,255,255,0.05); text-align: left; }}
  .channel-table th {{ color: var(--dim); font-weight: 500; font-size: .7rem; text-transform: uppercase; }}
  .status-chip {{ display: inline-block; padding: .15rem .55rem; border-radius: 9999px; font-family: 'JetBrains Mono', monospace; font-size: .68rem; letter-spacing: .04em; border: 1px solid; }}
  .restrictions-block ul {{ list-style: none; padding: 0; margin: 0; }}
  .restrictions-block li {{ background: rgba(220,38,38,0.07); border-left: 3px solid #dc2626; padding: 8px 12px; margin-bottom: 6px; border-radius: 4px; font-size: .85rem; }}
  .citations {{ margin-top: 14px; font-family: 'JetBrains Mono', monospace; font-size: .75rem; color: var(--dim); }}
  .hard-block-banner {{ display: flex; gap: 14px; align-items: center; background: rgba(220,38,38,0.15); border: 2px solid #dc2626; border-radius: 8px; padding: 14px 18px; margin-bottom: 16px; }}
  .hard-block-icon {{ font-size: 1.6rem; }}
  .hard-block-title {{ color: #fca5a5; font-weight: 700; letter-spacing: .05em; }}
  .hard-block-detail {{ color: #fee2e2; font-size: .85rem; margin-top: 2px; }}

  /* KPIs */
  .kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 14px; margin-bottom: 32px; }}
  .kpi {{ background: linear-gradient(135deg, rgba(17,17,24,.78), rgba(17,17,24,.45)); border: 1px solid rgba(255,255,255,.06); border-radius: 10px; padding: 16px 18px; }}
  .kpi-label {{ font-size: .7rem; color: var(--dim); text-transform: uppercase; letter-spacing: .1em; }}
  .kpi-value {{ font-size: 1.7rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; margin-top: 4px; }}

  /* Section cards */
  section.section {{
    background: linear-gradient(135deg, rgba(17,17,24,.78), rgba(17,17,24,.45));
    border: 1px solid rgba(255,255,255,.06); border-left: 4px solid var(--accent);
    border-radius: 12px; padding: 24px 28px; margin-bottom: 22px;
  }}
  .section-head {{ display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }}
  .section-icon {{ font-size: 1.4rem; }}
  .section-head h2 {{ font-family: 'Playfair Display', serif; color: var(--accent); margin: 0; font-size: 1.4rem; flex: 1; }}
  .section-count {{ font-family: 'JetBrains Mono', monospace; font-size: .8rem; color: var(--accent); background: rgba(255,255,255,0.04); padding: .2rem .7rem; border-radius: 9999px; }}

  .finding {{ padding: 12px 14px; border-radius: 6px; background: rgba(0,0,0,0.25); border: 1px solid rgba(255,255,255,0.04); margin-bottom: 8px; }}
  .finding-head {{ display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap; }}
  .finding-attribution {{ margin-left: auto; font-family: 'JetBrains Mono', monospace; font-size: .65rem; color: var(--dim); }}
  .finding-value {{ font-size: .92rem; color: var(--text); margin: 4px 0 6px; word-wrap: break-word; }}
  .finding-actions {{ font-size: .75rem; }}
  .src-link {{ color: var(--cyan); text-decoration: none; font-family: 'JetBrains Mono', monospace; }}
  .src-link:hover {{ color: var(--gold); text-decoration: underline; }}

  .chip {{ display: inline-block; padding: .15rem .55rem; border-radius: 9999px; font-size: .68rem; font-family: 'JetBrains Mono', monospace; letter-spacing: .04em; }}
  .chip-gold {{ background: rgba(201,168,76,.10); color: #e0c66a; border: 1px solid rgba(201,168,76,.3); }}
  .conf-chip {{ padding: .15rem .55rem; border-radius: 9999px; font-family: 'JetBrains Mono', monospace; font-size: .65rem; cursor: help; }}
  .conf-high {{ background: rgba(34,197,94,.12); color: #4ade80; border: 1px solid rgba(34,197,94,.4); }}
  .conf-med {{ background: rgba(201,168,76,.12); color: #e0c66a; border: 1px solid rgba(201,168,76,.4); }}
  .conf-low {{ background: rgba(220,38,38,.12); color: #f87171; border: 1px solid rgba(220,38,38,.4); }}

  /* Sources Run */
  .sources-run-section {{ margin-top: 32px; padding-top: 24px; border-top: 1px solid var(--line); }}
  .sources-run-section h3 {{ font-family: 'Playfair Display', serif; color: var(--gold); font-size: 1.2rem; margin-bottom: 14px; }}
  table.sources-table {{ width: 100%; border-collapse: collapse; background: var(--panel); border-radius: 8px; overflow: hidden; font-size: .85rem; }}
  table.sources-table th {{ padding: 10px 14px; background: rgba(201,168,76,.06); color: var(--gold); text-align: left; font-size: .7rem; text-transform: uppercase; letter-spacing: .08em; }}
  table.sources-table td {{ padding: 10px 14px; border-top: 1px solid rgba(255,255,255,0.04); }}
  table.sources-table td.num {{ font-family: 'JetBrains Mono', monospace; text-align: right; }}
  table.sources-table td.dim {{ color: var(--dim); font-size: .8rem; }}

  /* Legal footer */
  .legal-footer {{ margin-top: 40px; padding: 28px 32px; background: rgba(15,14,15,0.5); border: 1px solid var(--line); border-radius: 10px; }}
  .legal-footer h3 {{ font-family: 'Playfair Display', serif; color: var(--gold); margin: 0 0 16px; font-size: 1.3rem; }}
  .legal-block {{ font-size: .85rem; line-height: 1.6; color: var(--text); margin-bottom: 14px; }}
  .legal-block strong {{ color: var(--gold); }}
  .legal-block .quote {{ color: var(--gold-glow); font-style: italic; }}
  .legal-block code {{ font-family: 'JetBrains Mono', monospace; font-size: .82rem; color: var(--cyan); }}
  .warning-block {{ background: rgba(220,38,38,0.06); border-left: 3px solid var(--red); padding: 12px 16px; border-radius: 4px; }}

  /* TLDR Summary -- the part the operator actually reads */
  .tldr-card {{
    background: linear-gradient(135deg, rgba(201,168,76,0.15), rgba(201,168,76,0.03));
    border: 2px solid rgba(201,168,76,0.5); border-radius: 14px;
    padding: 28px 32px; margin-bottom: 28px;
    box-shadow: 0 0 60px rgba(201,168,76,0.12);
  }}
  .tldr-eyebrow {{ font-family: 'Playfair Display', serif; font-size: 1rem; color: var(--gold); letter-spacing: .12em; margin-bottom: 18px; }}
  .tldr-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px 32px; }}
  .tldr-block {{ }}
  .tldr-block-trust {{ grid-column: span 2; padding-top: 14px; border-top: 1px solid rgba(201,168,76,0.2); }}
  .tldr-block-action {{ grid-column: span 2; background: rgba(0,0,0,0.25); padding: 16px 20px; border-radius: 8px; }}
  .tldr-label {{ font-size: .7rem; text-transform: uppercase; letter-spacing: .2em; color: var(--gold); margin-bottom: 6px; font-weight: 600; }}
  .tldr-text {{ font-size: 1.05rem; line-height: 1.55; color: var(--text); }}
  .tldr-actions {{ list-style: none; padding: 0; margin: 0; }}
  .tldr-actions li {{ font-size: 1rem; line-height: 1.55; color: var(--text); padding: 4px 0; }}
  .tldr-actions li strong {{ color: var(--gold); }}

  /* Personalization + Pitch Hooks card */
  .personalization-card {{
    background: linear-gradient(135deg, rgba(139,92,246,0.10), rgba(34,211,238,0.04));
    border: 2px solid rgba(139,92,246,0.5);
    border-radius: 14px; padding: 28px 32px; margin-bottom: 28px;
    box-shadow: 0 0 60px rgba(139,92,246,0.10);
  }}
  .personalization-eyebrow {{ font-family: 'Playfair Display', serif; font-size: 1rem; color: #a78bfa; letter-spacing: .12em; margin-bottom: 18px; }}
  .personalization-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-bottom: 24px; padding-bottom: 24px; border-bottom: 1px solid rgba(139,92,246,0.2); }}
  .p-block {{ }}
  .p-label {{ font-size: .7rem; text-transform: uppercase; letter-spacing: .2em; color: #a78bfa; margin-bottom: 8px; font-weight: 600; }}
  .p-text {{ font-size: .95rem; line-height: 1.5; color: var(--text); }}
  .p-chips {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .p-empty {{ color: var(--dim); font-size: .85rem; font-style: italic; }}
  .pchip {{ padding: .25rem .7rem; border-radius: 9999px; font-size: .75rem;
            font-family: 'Inter', sans-serif; letter-spacing: .02em;
            font-weight: 500; }}
  .pchip-gold {{ background: rgba(201,168,76,0.12); color: #e0c66a; border: 1px solid rgba(201,168,76,0.4); }}
  .pchip-cyan {{ background: rgba(34,211,238,0.10); color: #67e8f9; border: 1px solid rgba(34,211,238,0.3); }}
  .pchip-red {{ background: rgba(220,38,38,0.10); color: #f87171; border: 1px solid rgba(220,38,38,0.3); }}
  .pchip-orange {{ background: rgba(249,115,22,0.10); color: #fb923c; border: 1px solid rgba(249,115,22,0.3); }}
  .pchip-dim {{ background: rgba(255,255,255,0.05); color: var(--dim); border: 1px solid rgba(255,255,255,0.15); }}

  .hooks-section {{ padding-top: 4px; }}
  .hook-row {{ display: flex; gap: 14px; margin-bottom: 12px; padding: 14px 16px;
                background: rgba(0,0,0,0.25); border: 1px solid rgba(255,255,255,0.06);
                border-radius: 8px; align-items: flex-start; }}
  .hook-cat-pill {{ flex-shrink: 0; padding: .25rem .65rem; border-radius: 9999px;
                     font-size: .65rem; text-transform: uppercase; letter-spacing: .1em;
                     font-weight: 600; font-family: 'JetBrains Mono', monospace; min-width: 80px; text-align: center; }}
  .hook-body {{ flex: 1; }}
  .hook-text {{ font-size: 1rem; line-height: 1.5; color: var(--text); font-weight: 500; }}
  .hook-rationale {{ margin-top: 6px; font-size: .78rem; line-height: 1.4; color: var(--dim); font-style: italic; }}
  .hook-rationale-label {{ color: #a78bfa; font-style: normal; font-weight: 600; margin-right: 4px; }}
  .personalization-footer {{ font-size: .78rem; line-height: 1.5; color: var(--dim);
                              padding-top: 14px; margin-top: 18px; border-top: 1px solid rgba(255,255,255,0.05); }}

  /* Profile Depth card */
  .depth-card {{
    background: linear-gradient(135deg, rgba(34,211,238,0.10), rgba(34,211,238,0.02));
    border: 2px solid rgba(34,211,238,0.4); border-radius: 14px;
    padding: 24px 28px; margin-bottom: 24px;
  }}
  .depth-eyebrow {{ font-family: 'Playfair Display', serif; font-size: .95rem; color: var(--cyan); letter-spacing: .12em; margin-bottom: 14px; }}
  .depth-score-row {{ display: flex; align-items: baseline; gap: 18px; margin-bottom: 16px; padding-bottom: 14px; border-bottom: 1px solid rgba(34,211,238,0.2); }}
  .depth-score {{ font-size: 2.6rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }}
  .depth-score-suffix {{ font-size: 1rem; color: var(--dim); margin-left: 4px; }}
  .depth-verdict {{ font-size: 1rem; color: var(--text); }}
  .depth-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
  .depth-axes {{ display: flex; flex-direction: column; gap: 6px; }}
  .depth-axis {{ display: grid; grid-template-columns: 1fr 80px 30px; gap: 10px; align-items: center; font-size: .82rem; }}
  .depth-axis-label {{ color: var(--text); }}
  .depth-axis-bar {{ height: 8px; background: rgba(255,255,255,.05); border-radius: 4px; overflow: hidden; }}
  .depth-axis-bar > span {{ display: block; height: 100%; border-radius: 4px; }}
  .depth-axis-score {{ font-family: 'JetBrains Mono', monospace; color: var(--gold); font-size: .8rem; text-align: right; }}
  .rec-row {{ padding: 8px 12px; background: rgba(0,0,0,0.2); border-left: 2px solid var(--cyan); border-radius: 4px; margin-bottom: 6px; font-size: .8rem; }}
  .rec-axis {{ color: var(--cyan); font-family: 'JetBrains Mono', monospace; font-size: .7rem; text-transform: uppercase; margin-bottom: 2px; }}
  .rec-text {{ color: var(--text); }}

  /* Pitch Package */
  .pkg-card {{
    background: linear-gradient(135deg, rgba(201,168,76,0.10), rgba(139,92,246,0.04));
    border: 2px solid rgba(201,168,76,0.5); border-radius: 14px;
    padding: 28px 32px; margin-bottom: 28px;
    box-shadow: 0 0 60px rgba(201,168,76,0.10);
  }}
  .pkg-eyebrow {{ font-family: 'Playfair Display', serif; font-size: 1.05rem; color: var(--gold); letter-spacing: .12em; margin-bottom: 18px; }}
  .pkg-stage {{ margin-bottom: 22px; }}
  .pkg-stage-label {{ font-size: .72rem; text-transform: uppercase; letter-spacing: .18em; color: #a78bfa; margin-bottom: 10px; padding-bottom: 6px; border-bottom: 1px dashed rgba(139,92,246,0.25); font-weight: 600; }}
  .pkg-stage-body {{ }}
  .pkg-row {{ display: flex; align-items: center; gap: 12px; margin-bottom: 8px; flex-wrap: wrap; }}
  .pkg-row-label {{ font-size: .7rem; text-transform: uppercase; letter-spacing: .12em; color: var(--dim); min-width: 110px; }}
  .angle-row {{ display: flex; gap: 14px; padding: 10px 14px; background: rgba(0,0,0,0.25); border-radius: 6px; margin-bottom: 8px; align-items: flex-start; }}
  .angle-text {{ flex: 1; font-size: .92rem; line-height: 1.5; color: var(--text); }}
  .touchpoint {{ background: rgba(0,0,0,0.3); border-left: 3px solid var(--gold); border-radius: 6px; padding: 16px 20px; margin-bottom: 14px; }}
  .tp-head {{ display: flex; align-items: center; gap: 12px; margin-bottom: 8px; flex-wrap: wrap; }}
  .tp-step {{ background: rgba(201,168,76,.15); color: var(--gold); padding: .2rem .8rem; border-radius: 9999px; font-size: .7rem; font-family: 'JetBrains Mono', monospace; font-weight: 600; }}
  .tp-name {{ font-family: 'Playfair Display', serif; font-size: 1.1rem; color: var(--gold); }}
  .tp-when {{ font-family: 'JetBrains Mono', monospace; font-size: .7rem; color: var(--dim); margin-left: auto; }}
  .tp-rationale {{ font-size: .75rem; color: var(--dim); font-style: italic; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px dashed rgba(255,255,255,0.05); }}
  .ch-block {{ margin-bottom: 12px; padding: 10px 14px; background: rgba(0,0,0,0.25); border-radius: 4px; }}
  .ch-label {{ font-size: .68rem; text-transform: uppercase; letter-spacing: .12em; color: var(--gold); margin-bottom: 6px; font-family: 'JetBrains Mono', monospace; }}
  .ch-label em {{ color: var(--text); font-style: italic; text-transform: none; letter-spacing: 0; }}
  .ch-body {{ font-size: .9rem; line-height: 1.55; color: var(--text); }}
  .ch-mono {{ font-family: 'JetBrains Mono', monospace; font-size: .82rem; }}
  .route-primary {{ font-size: .9rem; color: var(--text); margin-bottom: 8px; }}
  .route-step {{ font-size: .8rem; color: var(--dim); padding: 4px 0; font-family: 'JetBrains Mono', monospace; }}
  .pkg-footer {{ font-size: .78rem; line-height: 1.5; color: var(--dim); padding-top: 14px; margin-top: 14px; border-top: 1px solid rgba(255,255,255,0.05); }}

  /* Garbage / low-value findings collapsible */
  details.garbage-section {{ margin: 32px 0; background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.05); border-radius: 8px; padding: 4px 0; }}
  details.garbage-section summary {{ cursor: pointer; padding: 14px 20px; font-size: .85rem; color: var(--dim); user-select: none; }}
  details.garbage-section summary:hover {{ color: var(--gold); }}
  details.garbage-section[open] summary {{ color: var(--gold); border-bottom: 1px solid rgba(255,255,255,0.05); }}
  .garbage-summary-icon {{ margin-right: 8px; }}
  .garbage-body {{ padding: 12px 20px 20px; }}
  .garbage-row {{ display: grid; grid-template-columns: 110px 130px 1fr auto 90px; gap: 12px; align-items: center; padding: 8px 0; border-bottom: 1px dashed rgba(255,255,255,0.04); font-size: .82rem; }}
  .garbage-row:last-child {{ border-bottom: none; }}
  .garbage-reason {{ color: var(--dim); font-family: 'JetBrains Mono', monospace; font-size: .72rem; }}
  .garbage-label {{ color: var(--gold); font-size: .8rem; font-weight: 500; }}
  .garbage-value {{ color: var(--text); opacity: .7; }}
  .garbage-investigator {{ color: var(--dim); font-family: 'JetBrains Mono', monospace; font-size: .68rem; text-align: right; }}

  .empty-state {{ color: var(--dim); font-style: italic; font-size: .9rem; padding: 12px 0; }}
  .empty-state-large {{ background: rgba(255,255,255,0.02); border: 1px dashed rgba(255,255,255,0.15); padding: 36px; border-radius: 8px; text-align: center; color: var(--dim); }}

  footer.report-footer {{ border-top: 1px solid var(--line); padding: 24px 56px; color: var(--dim); font-size: .8rem; text-align: center; position: relative; z-index: 2; }}
  footer.report-footer code {{ font-family: 'JetBrains Mono', monospace; color: var(--gold); }}

  @media (max-width: 768px) {{
    header, main {{ padding-left: 24px; padding-right: 24px; }}
    .legal-panel-grid {{ grid-template-columns: 1fr; }}
    h1 {{ font-size: 1.8rem; }}
  }}
</style>
</head>
<body>
<div class="mesh"></div>
<div class="view-stamp">INTERNAL · {viewer} · {view_ts}</div>

<header>
  <div class="wordmark">Everlight Ventures · Intel Center</div>
  <h1>{target} <span class="kind-chip">{kind}</span></h1>
  <div class="header-meta">
    investigation_id: <span class="gold">{inv_id}</span> · started: <span class="gold">{started_at}</span> ·
    triggered by: <span class="gold">{triggered_by}</span>
  </div>
</header>

<main>
  {dnc_html}
  {tldr_html}
  {depth_html}
  {pkg_html}
  {personalization_html}
  {state_panel_html}

  <div class="kpis">{kpi_html}</div>

  {sec_html}

  {garbage_html}

  <section class="sources-run-section">
    <h3>Sources Run</h3>
    <table class="sources-table">
      <thead><tr><th>Investigator</th><th>Status</th><th class="num">Verified / Raw</th><th class="num">Elapsed</th><th>Notes</th></tr></thead>
      <tbody>{''.join(src_rows)}</tbody>
    </table>
  </section>

  {legal_html}
</main>

<footer class="report-footer">
  Lucrex · Everlight Ventures · Intel Center · Report rendered {view_ts} ·
  Re-run with <code>intel investigate "{target}"</code>
</footer>
</body>
</html>"""
