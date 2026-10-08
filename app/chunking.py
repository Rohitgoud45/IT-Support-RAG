"""Two chunking strategies so you can compare them in the eval."""
import re


def chunk_fixed(text: str, size: int = 800, overlap: int = 150) -> list[str]:
    """Sliding character window."""
    text = text.strip()
    if not text:
        return []
    step = max(size - overlap, 1)
    pieces = (text[i : i + size] for i in range(0, len(text), step))
    return [p for p in pieces if p.strip()]


def chunk_paragraph(text: str, size: int = 800, overlap: int = 150) -> list[str]:
    """Pack whole paragraphs up to `size` chars; carry a short tail into the next chunk."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    cur = ""
    for p in paras:
        if len(p) > size:
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.extend(chunk_fixed(p, size, overlap))
            continue
        if not cur:
            cur = p
        elif len(cur) + len(p) + 2 <= size:
            cur = f"{cur}\n\n{p}"
        else:
            chunks.append(cur)
            tail = cur[-overlap:] if overlap else ""
            cur = f"{tail}\n\n{p}" if tail else p
    if cur:
        chunks.append(cur)
    return chunks


def chunk_text(text: str, strategy: str = "paragraph", size: int = 800, overlap: int = 150) -> list[str]:
    if strategy == "fixed":
        return chunk_fixed(text, size, overlap)
    if strategy == "paragraph":
        return chunk_paragraph(text, size, overlap)
    raise ValueError(f"Unknown chunk strategy: {strategy}")
