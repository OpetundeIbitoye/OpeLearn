"""Section-aware chunks, a strict 600-token ceiling, and about 15% overlap.

Tables larger than the ceiling are rejected explicitly: silently splitting or
truncating one would violate passage provenance.
"""

from typing import Protocol

from app.corpus.schemas import Block, ChunkText


class Tokenizer(Protocol):
    def encode(self, text: str, *, add_special_tokens: bool = False) -> list[int]: ...


def chunk_blocks(blocks: list[Block], tokenizer: Tokenizer, ceiling: int = 600) -> list[ChunkText]:
    if not 1 <= ceiling <= 600:
        raise ValueError("Token ceiling must be between 1 and 600")
    result: list[ChunkText] = []
    pending = ""
    origin: Block | None = None
    overlap_tokens = int(ceiling * 0.15)

    def count(value: str) -> int:
        return len(tokenizer.encode(value, add_special_tokens=False))

    def flush() -> None:
        nonlocal pending
        if pending.strip() and origin is not None:
            result.append(
                ChunkText(
                    text=pending.strip(),
                    section_heading=origin.section_heading,
                    page_number=origin.page_number,
                    token_count=count(pending.strip()),
                )
            )
        pending = ""

    for block in blocks:
        if not block.text.strip():
            continue
        if origin is not None and block.section_heading != origin.section_heading:
            flush()
        if block.kind == "table":
            flush()
            if count(block.text) > ceiling:
                raise ValueError(f"Table exceeds {ceiling} tokens on page {block.page_number}")
            result.append(
                ChunkText(
                    text=block.text,
                    section_heading=block.section_heading,
                    page_number=block.page_number,
                    token_count=count(block.text),
                )
            )
            origin = None
            continue
        # Slice the original text rather than decoding token IDs, preserving verbatim passages.
        remaining = block.text.strip()
        while remaining:
            if not pending:
                origin = block
            joined = pending + ("\n\n" if pending else "") + remaining
            if count(joined) <= ceiling:
                pending = joined
                break
            if pending:
                previous = pending
                flush()
                # Retain the final complete words as overlap only within this section.
                words = previous.split()
                tail: list[str] = []
                for word in reversed(words):
                    if count(" ".join([word, *tail])) > overlap_tokens:
                        break
                    tail.insert(0, word)
                pending = " ".join(tail)
                origin = block
                if pending and count(pending + "\n\n" + remaining) <= ceiling:
                    pending += "\n\n" + remaining
                    break
            prefix = pending + ("\n\n" if pending else "")
            low, high = 0, len(remaining)
            while low < high:
                middle = (low + high + 1) // 2
                if count(prefix + remaining[:middle]) <= ceiling:
                    low = middle
                else:
                    high = middle - 1
            if low == 0:
                pending = ""
                raise ValueError("Cannot fit a text character within token ceiling")
            boundary = remaining.rfind(" ", 0, low)
            cut = boundary if boundary > 0 else low
            pending = prefix + remaining[:cut]
            flush()
            remaining = remaining[cut:].lstrip()
            if remaining:
                previous = result[-1].text.split()
                tail = []
                for word in reversed(previous):
                    if count(" ".join([word, *tail])) > overlap_tokens:
                        break
                    tail.insert(0, word)
                pending = " ".join(tail)
                origin = block
    flush()
    return result
