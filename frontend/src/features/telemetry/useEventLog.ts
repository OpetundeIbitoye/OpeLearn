import { useCallback, useEffect, useRef } from "react";
import { studyHeaders } from "../consent/ConsentGate";

export type EventType = "citation_click" | "passage_expand" | "scroll_depth" | "copy" | "query_revision" | "scaffold_shown" | "scaffold_accepted" | "scaffold_dismissed";
export interface InteractionEvent { type: EventType; target?: string; dwellMs?: number; clientTs: number; }

export function useEventLog() {
  const buffer = useRef<InteractionEvent[]>([]);
  const flush = useCallback(() => {
    if (!buffer.current.length) return;
    const events = buffer.current.splice(0).map((event) => ({ event_type: event.type,
      payload: { target: event.target, dwell_ms: event.dwellMs },
      client_timestamp: new Date(event.clientTs).toISOString() }));
    const body = JSON.stringify({ session_id: localStorage.getItem("sessionId"), events });
    if (document.visibilityState === "hidden") {
      fetch("/study/events", { method: "POST", headers: { "content-type": "application/json", ...studyHeaders() }, body, keepalive: true });
    } else fetch("/study/events", { method: "POST", headers: { "content-type": "application/json", ...studyHeaders() }, body });
  }, []);
  useEffect(() => { const timer = window.setInterval(flush, 5000);
    const visibility = () => { if (document.visibilityState === "hidden") flush(); };
    document.addEventListener("visibilitychange", visibility);
    return () => { window.clearInterval(timer); document.removeEventListener("visibilitychange", visibility); flush(); };
  }, [flush]);
  return { logEvent: (event: InteractionEvent) => buffer.current.push(event), flush };
}
