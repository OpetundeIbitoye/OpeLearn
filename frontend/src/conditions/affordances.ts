// Single map from arm to what the interface renders.
//
// Every conditional affordance in the UI reads from here. No component
// should ever check `arm === "A3"` directly — if it does, the manipulation
// has leaked out of config/arms.yaml and into the component tree.

export type ArmId = "A1" | "A2" | "A3";

export interface Affordances {
  showSynthesisedAnswer: boolean;
  showInlineCitations: boolean;
  showRetrievedPassages: boolean;
  showQualityAnnotations: boolean;
  showSocraticPrompt: boolean;
  allowQueryRefinement: boolean;
  showSourceComparison: boolean;
  showEndReflection: boolean;
}

// Fetched from GET /study/session at session start — never hardcoded per build.
export function affordancesFor(arm: ArmId, config: Affordances): Affordances {
  return config;
}
