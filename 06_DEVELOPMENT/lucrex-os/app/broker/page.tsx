import { ComingSoon } from "@/components/ComingSoon";

export default function BrokerPage() {
  return (
    <ComingSoon
      title="Broker OS"
      domain="Broker"
      accent="#B8902F"
      themeClass="theme-broker"
      blurb="B2B SaaS matchmaking. 15-30% finder fees. First deal already in pipeline at $47.50 intro."
      willInclude={[
        "Deal pipeline with stage kanban (intro, qualified, proposal, contract, closed, paid)",
        "Commission tracker with Stripe invoicing integration",
        "Active matches feed from match_maker agent",
        "Outreach campaign performance",
        "Compliance status from contract_attorney + finder_scope checks",
      ]}
    />
  );
}
