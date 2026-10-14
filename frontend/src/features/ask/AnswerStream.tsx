import { Fragment } from "react";
import { CitationChip } from "./CitationChip";

type Props = {
  answer: string;
  loading: boolean;
  onCitation: (marker: number) => void;
  showCitations: boolean;
  heading: string;
};

export function AnswerStream({ answer, loading, onCitation, showCitations, heading }: Props) {
  return <section aria-live="polite"><h2>{heading}</h2><p>
    {answer.split(/(\[\d+\])/g).map((part, index) => {
      const match = part.match(/^\[(\d+)\]$/);
      return match && showCitations ? (
        <Fragment key={`${part}-${index}`}>
          <CitationChip marker={Number(match[1])} onClick={onCitation} />
        </Fragment>
      ) : (
        <Fragment key={`${part}-${index}`}>{part}</Fragment>
      );
    })}
    {loading && <span aria-label="Generating"> ▍</span>}
  </p></section>;
}
