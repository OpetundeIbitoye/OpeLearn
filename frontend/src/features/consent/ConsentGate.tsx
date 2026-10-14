import { FormEvent, ReactNode, useEffect, useState } from "react";

export function studyHeaders(): Record<string, string> {
  const participant = localStorage.getItem("participantId");
  const session = localStorage.getItem("sessionId");
  return {
    ...(participant ? { "x-participant-id": participant } : {}),
    ...(session ? { "x-session-id": session } : {}),
  };
}

export function ConsentGate({ children }: { children: ReactNode }) {
  const [text, setText] = useState("");
  const [version, setVersion] = useState("");
  const [ready, setReady] = useState(Boolean(localStorage.getItem("sessionId")));
  const [accepted, setAccepted] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!ready) fetch("/study/consent").then((response) => response.json()).then((body) => {
      setText(String(body.text)); setVersion(String(body.version));
    }).catch((cause) => setError(String(cause)));
  }, [ready]);

  async function submit(event: FormEvent) {
    event.preventDefault(); setError("");
    try {
      let participantId = localStorage.getItem("participantId");
      if (!participantId) {
        const enrolled = await fetch("/study/participants", { method: "POST" });
        const body = await enrolled.json(); participantId = String(body.participant_id);
        localStorage.setItem("participantId", participantId);
      }
      const consent = await fetch("/study/consent", {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ participant_id: participantId, version, accepted }),
      });
      if (!consent.ok) throw new Error(`Consent failed: ${consent.status}`);
      const session = await fetch("/study/sessions", {
        method: "POST",
        headers: { "content-type": "application/json", "x-participant-id": participantId },
        body: JSON.stringify({ participant_id: participantId }),
      });
      if (!session.ok) throw new Error(`Session failed: ${session.status}`);
      const body = await session.json(); localStorage.setItem("sessionId", String(body.session_id));
      setReady(true);
    } catch (cause) { setError(String(cause)); }
  }

  if (ready) return <>{children}</>;
  return <main><h1>Research consent</h1><p>{text || "Loading consent…"}</p>
    <form onSubmit={submit}><label><input type="checkbox" checked={accepted}
      onChange={(event) => setAccepted(event.target.checked)} /> I consent to participate.</label>
      <button disabled={!accepted || !version}>Continue</button></form>
    {error && <p role="alert">{error}</p>}</main>;
}
