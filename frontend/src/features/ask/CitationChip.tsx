type Props = { marker: number; onClick: (marker: number) => void };

export function CitationChip({ marker, onClick }: Props) {
  return <button type="button" onClick={() => onClick(marker)}>[{marker}]</button>;
}
