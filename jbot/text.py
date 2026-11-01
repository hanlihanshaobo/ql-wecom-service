"""文本分片工具。"""

from __future__ import annotations

# 企业微信 text 消息 content 最大 2048 字节，留一点余量。
MAX_TEXT_BYTES = 1900


def split_text(content: str, limit: int = MAX_TEXT_BYTES) -> list[str]:
    """按 UTF-8 字节数切分长文本，尽量保持整行。"""
    if not content:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_bytes = 0

    for line in content.splitlines(keepends=True):
        line_bytes = len(line.encode("utf-8"))
        if line_bytes > limit:
            # 单行过长，先冲刷当前块，再按字节硬切。
            if current:
                chunks.append("".join(current))
                current, current_bytes = [], 0
            piece: list[str] = []
            piece_bytes = 0
            for char in line:
                size = len(char.encode("utf-8"))
                if piece_bytes + size > limit:
                    chunks.append("".join(piece))
                    piece, piece_bytes = [], 0
                piece.append(char)
                piece_bytes += size
            if piece:
                current, current_bytes = piece, piece_bytes
            continue

        if current_bytes + line_bytes > limit and current:
            chunks.append("".join(current))
            current, current_bytes = [], 0
        current.append(line)
        current_bytes += line_bytes

    if current:
        chunks.append("".join(current))

    return [chunk for chunk in chunks if chunk.strip()]
