import { useCallback, useState } from "react";
import { studyHeaders } from "../consent/ConsentGate";

export type Source = {
  marker: number;
  chunk_id: string;
  text: string;
  section_heading: string;
  page_number: number;
};

function parseFrame(raw: string) {
  const lines = raw.split("\n");
  const event = lines.find((line) => line.startsWith("event: "))?.slice(7);
  const data = lines.find((line) => line.startsWith("data: "))?.slice(6);
  return event && data ? { event, data: JSON.parse(data) as Record<string, unknown> } : null;
}

export function useAsk(endpoint = "/ask") {
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<Source[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const ask = useCallback(async (query: string) => {
    setAnswer(""); setSources([]); setError(""); setLoading(true);
    try {
      const response = await fetch(endpoint, {
        method: "POST", headers: { "content-type": "application/json", ...studyHeaders() },
        body: JSON.stringify({ query }),
      });
      if (!response.ok || !response.body) throw new Error(`Ask request failed: ${response.status}`);
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";
        for (const raw of parts) {
          const frame = parseFrame(raw);
          if (!frame) continue;
          if (frame.event === "token") setAnswer((current) => current + String(frame.data.text));
          if (frame.event === "sources") setSources(frame.data.sources as Source[]);
          if (frame.event === "error") throw new Error(String(frame.data.message));
        }
        if (done) break;
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally { setLoading(false); }
  }, [endpoint]);

  return { answer, sources, error, loading, ask };
}
