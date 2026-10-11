"""Pure replacement of one exact LF-delimited marker block; never a writer."""
import hashlib

from .canonical import ContractError, bounded_text, digest_text, identifier


def tex_text(text):
    escapes = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "&": r"\&",
               "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
               "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(escapes.get(char, char) for char in text)


def preview_marked_text(source, marker, text, expected_digest):
    identifier(marker)
    bounded_text(text)
    digest_text(expected_digest)
    if type(source) is not bytes or len(source) > 65536 or hashlib.sha256(source).hexdigest() != expected_digest:
        raise ContractError("marked source changed or exceeds the fixture bound")
    start = f"% claimbranch:start id={marker}\n".encode()
    end = f"% claimbranch:end id={marker}\n".encode()
    lines = source.splitlines(keepends=True)
    starts = [index for index, line in enumerate(lines) if line == start]
    ends = [index for index, line in enumerate(lines) if line == end]
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        raise ContractError("exact unique ordered LF markers required")
    return b"".join(lines[:starts[0] + 1]) + tex_text(text).encode("utf-8") + b"\n" + b"".join(lines[ends[0]:])
