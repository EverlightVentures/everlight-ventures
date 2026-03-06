# Everlight Ventures -- Site Architecture

## Domain
- **Primary:** everlightventures.io (Namecheap)
- **Hosting:** Lovable (public-facing)
- **Ops Dashboard:** Django hive_dashboard (private, localhost:8502)

## Site Structure (everlightventures.io)

All ventures are tabs/sections under one Lovable project.

```
everlightventures.io
|
|-- / (Home)              Everlight Ventures brand hub
|-- /him-loadout          HIM Gear Drop -- affiliate gear site
|-- /logistics            Everlight Logistics LLC -- shipping/ops
|-- /publishing           Publishing arm (parent section)
|   |-- /beyond-the-avels   Book series
|   |-- /tsw                Book series
|   |-- /everlight-kids     Children's brand (Sam & Robo characters)
|-- /alley-kingz          Alley Kingz -- PvP mobile game (Clash Carbon)
|-- /onyx                 Onyx POS -- point-of-sale SaaS
|-- /hivemind             Hive Mind -- AI orchestration SaaS
```

## Existing Lovable Apps
- him-gear-drop.lovable.app -- affiliate site (to be integrated as /him-loadout)

## Business Structure
- **Everlight Ventures** = Parent brand (umbrella)
- **Everlight Logistics LLC** = Legal entity (subsidiary)
- All products/ventures operate under the Everlight Ventures umbrella

## Integration Points
- Lovable: Public site builder + hosting
- Lovable integrations: Slack, ElevenLabs, GitHub
- Django: Private ops dashboard, taskboard, funnel analytics
- Namecheap: DNS management
