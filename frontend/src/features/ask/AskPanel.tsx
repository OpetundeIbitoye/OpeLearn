import { FormEvent, useState } from "react";
import { AnswerStream } from "./AnswerStream";
import { SourcePanel } from "./SourcePanel";
import { useAsk } from "./useAsk";
import { useArmConditions } from "../../conditions/ArmProvider";

export function AskPanel() {
  const { affordances, askUrl, error: conditionError } = useArmConditions();
  const [query, setQuery] = useState("");
  const { answer, sources, error, loading, ask } = useAsk(askUrl);
  function submit(event: FormEvent) {
    event.preventDefault();
    if (query.trim() && !loading) void ask(query.trim());
  }
  function openCitation(marker: number) {
    const source = document.getElementById(`source-${marker}`);
    source?.scrollIntoView({ behavior: "smooth", block: "center" }); source?.focus();
  }
  return <>
    {conditionError && <p role="alert">{conditionError}</p>}
    <form onSubmit={submit}>
      <label htmlFor="question">Ask a question about the local corpus</label>
      <textarea id="question" value={query} onChange={(event) => setQuery(event.target.value)} />
      <button type="submit" disabled={loading || !query.trim()}>{loading ? "Answering…" : "Ask"}</button>
    </form>
    {error && <p role="alert">{error}</p>}
    {(answer || loading) && affordances && <AnswerStream
      answer={answer}
      loading={loading}
      onCitation={openCitation}
      showCitations={affordances.showInlineCitations}
      heading={affordances.showSynthesisedAnswer ? "Answer" : "Retrieved passages"}
    />}
    {affordances?.showRetrievedPassages && <SourcePanel sources={sources} />}
  </>;
}
