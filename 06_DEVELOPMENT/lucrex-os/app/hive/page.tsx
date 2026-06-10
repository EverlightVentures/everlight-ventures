import { ComingSoon } from "@/components/ComingSoon";

export default function HivePage() {
  return (
    <ComingSoon
      title="Hive"
      domain="Hive"
      accent="#3B82F6"
      themeClass="theme-hive"
      blurb="63 agents across 12 fire teams in 4 squads. Marcus Cole leads Claude Corp."
      willInclude={[
        "Agent roster grid (63 cards) with personality + speech style + relationships",
        "Live dispatch feed: which agents are working which task",
        "Fire team status with buddy pair health",
        "Agent performance metrics (deals worked, deliverables shipped, errors caught)",
        "One-click dispatch: send a query to a named agent or fire team",
      ]}
    />
  );
}
