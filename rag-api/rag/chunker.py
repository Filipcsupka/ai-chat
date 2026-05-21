"""
Split markdown text into overlapping chunks for embedding.

Each chunk keeps its source filename so retrieved context can reference it.
Splitting strategy: paragraph-aware — prefer splitting at blank lines, fall
back to hard character limit with overlap to preserve sentence context.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Chunk:
    text: str
    source: str   # filename without extension
    index: int    # chunk number within source


def _split_paragraphs(text: str, source: str, chunk_size: int, overlap: int) -> list[Chunk]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[Chunk] = []
    current = ""
    idx = 0

    for para in paragraphs:
        candidate = (current + "\n\n" + para).strip() if current else para
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(Chunk(text=current, source=source, index=idx))
                idx += 1
                # keep last `overlap` chars as context seed for next chunk
                current = current[-overlap:] + "\n\n" + para if overlap else para
            else:
                # single paragraph longer than chunk_size — hard split
                for start in range(0, len(para), chunk_size - overlap):
                    chunk_text = para[start : start + chunk_size]
                    chunks.append(Chunk(text=chunk_text, source=source, index=idx))
                    idx += 1
                current = ""

    if current:
        chunks.append(Chunk(text=current, source=source, index=idx))

    return chunks


def chunk_file(path: Path, chunk_size: int = 500, overlap: int = 50) -> list[Chunk]:
    """Read a markdown file and return a list of Chunk objects."""
    text = path.read_text(encoding="utf-8")
    source = path.stem  # e.g. "profile", "experience"
    return _split_paragraphs(text, source, chunk_size, overlap)


def chunk_directory(directory: Path, chunk_size: int = 500, overlap: int = 50) -> list[Chunk]:
    """Chunk all .md files in a directory."""
    chunks: list[Chunk] = []
    for md_file in sorted(directory.glob("*.md")):
        chunks.extend(chunk_file(md_file, chunk_size, overlap))
    return chunks
