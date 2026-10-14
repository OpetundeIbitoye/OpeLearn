import { FormEvent, useEffect, useState } from "react";
import { studyHeaders } from "../consent/ConsentGate";

type Instrument = { id: string; trigger: string; scale: { min: number; max: number; anchors: string[] }; items: { id: string; wording: string }[] };

export function SurveyModal({ trigger, onComplete }: { trigger: string; onComplete: () => void }) {
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [responses, setResponses] = useState<Record<string, number>>({});
  useEffect(() => { fetch(`/study/surveys/${trigger}`, { headers: studyHeaders() })
    .then((response) => response.json()).then(setInstruments); }, [trigger]);
  if (!instruments.length) return null;
  async function submit(event: FormEvent) {
    event.preventDefault();
    for (const instrument of instruments) await fetch("/study/surveys", {
      method: "POST", headers: { "content-type": "application/json", ...studyHeaders() },
      body: JSON.stringify({ session_id: localStorage.getItem("sessionId"), instrument: instrument.id,
        trigger, responses: Object.fromEntries(instrument.items.map((item) => [item.id, responses[`${instrument.id}.${item.id}`]])) }),
    });
    onComplete();
  }
  return <dialog open><form onSubmit={submit}><h2>Short survey</h2>{instruments.flatMap((instrument) =>
    instrument.items.map((item) => <label key={`${instrument.id}.${item.id}`}>{item.wording}
      <input type="number" required min={instrument.scale.min} max={instrument.scale.max}
        onChange={(event) => setResponses((value) => ({ ...value, [`${instrument.id}.${item.id}`]: Number(event.target.value) }))} />
    </label>))}<button>Submit</button></form></dialog>;
}
