import type { Source } from "./useAsk";

export function SourcePanel({ sources }: { sources: Source[] }) {
  if (!sources.length) return null;
  return <aside><h2>Sources</h2>{sources.map((source) => (
    <article id={`source-${source.marker}`} key={source.chunk_id} tabIndex={-1}>
      <h3>[{source.marker}] {source.section_heading}</h3>
      <p>Page {source.page_number}</p>
      <blockquote>{source.text}</blockquote>
    </article>
  ))}</aside>;
}
