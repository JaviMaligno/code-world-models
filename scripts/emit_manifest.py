"""SHA-256 manifest of the paper-facing artifacts.

Covers every tracked JSON under results/ (both papers share the
directory) and the paper sources. Emits MANIFEST.sha256 at the repo
root, one `<hash>  <posix-path>` line per file, sorted by path — the
checksum half of the archival TODO (REVIEW-CODEX.md round-1 #11).

Run after any campaign or tex change that should be part of the
archived snapshot: `python scripts/emit_manifest.py`.
"""
import hashlib
import pathlib
import subprocess

_REPO = pathlib.Path(__file__).resolve().parents[1]
DST = _REPO / "MANIFEST.sha256"


def tracked(pattern: str):
    out = subprocess.run(
        ["git", "ls-files", pattern], cwd=_REPO,
        capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if line]


def main() -> None:
    paths = sorted(
        set(tracked("results/*.json"))
        | set(tracked("docs/paper3/*.tex"))
        | set(tracked("docs/paper3/*.md"))
        | set(tracked("env-lock.txt")))
    lines = []
    for rel in paths:
        h = hashlib.sha256((_REPO / rel).read_bytes()).hexdigest()
        lines.append(f"{h}  {rel}")
    DST.write_text("\n".join(lines) + "\n")
    print(f"wrote {DST} ({len(lines)} files)")


if __name__ == "__main__":
    main()
