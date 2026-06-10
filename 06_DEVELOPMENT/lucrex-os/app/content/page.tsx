import { ComingSoon } from "@/components/ComingSoon";

export default function ContentPage() {
  return (
    <ComingSoon
      title="Content Factory"
      domain="Content"
      accent="#EC4899"
      themeClass="theme-content"
      blurb="Queue, schedule, repurpose. avatar_orchestrator into social_poster into funnel_nurture."
      willInclude={[
        "Content queue from 02_CONTENT_FACTORY/01_Queue/",
        "Scheduled posts across IG, X, LinkedIn",
        "Repurposing pipeline (long-form to clips to threads)",
        "Asset library + IG Digital Launch Kit (8 templates)",
        "Funnel nurture sequence performance",
      ]}
    />
  );
}
