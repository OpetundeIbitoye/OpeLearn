// Interaction event capture. Deliberately NOT an analytics SDK: we need exact
// timestamps, guaranteed delivery, and our own schema.
//
// Batches events and flushes on interval + visibilitychange (so a closed tab
// does not silently drop the tail of a session).

export type EventType =
  | "citation_click"
  | "passage_expand"
  | "scroll_depth"
  | "copy"
  | "query_revision"
  | "scaffold_shown"
  | "scaffold_accepted"
  | "scaffold_dismissed";

export interface InteractionEvent {
  type: EventType;
  target?: string;
  dwellMs?: number;
  clientTs: number;
}

// TODO: implement buffer + flush to POST /study/events
