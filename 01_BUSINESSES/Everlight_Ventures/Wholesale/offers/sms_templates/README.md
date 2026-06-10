# SMS Templates

Every template must:
- Include sender identity (Piper / Everlight Ventures)
- Include STOP opt-out language
- Fit one SMS segment (160 chars) when possible, never more than two
- Use lowercase interpolation tokens: `{first_name}`, `{address}`, `{city}`, etc.

**Gate:** SMS sends are blocked until Twilio A2P 10DLC is approved AND `A2P_APPROVED=1` in the env. Email is the only live channel until then.

**Review:** Justine Park reviews every template in one batch before the A2P campaign filing. No SMS goes live without her sign-off logged in the compliance gate.
