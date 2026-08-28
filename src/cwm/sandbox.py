"""Run untrusted generated code in an isolated subprocess."""
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass

@dataclass
class SandboxResult:
    ok: bool
    stdout: str
    stderr: str
    timed_out: bool

def run_in_sandbox(code: str, call: str, timeout: float = 5.0) -> SandboxResult:
    source = code + "\n" + call + "\n"
    # encoding is pinned, not left to the locale: a .py file with no coding
    # declaration is read as UTF-8 by the interpreter (PEP 3120), while an
    # unpinned text handle writes in locale.getpreferredencoding() -- cp1252 on
    # a Spanish Windows. Any non-ASCII character in the code (an em dash in a
    # docstring is enough) then came back as "SyntaxError: Non-UTF-8 code
    # starting with '\x97'", i.e. every case scored as an execution error on
    # that machine and as a pass everywhere else.
    f = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                    encoding="utf-8")
    try:
        f.write(source)
        f.flush()
        f.close()  # close before the subprocess opens it (also required on Windows)
        try:
            proc = subprocess.run(
                [sys.executable, "-I", f.name],   # -I: isolated, ignore env & user site
                capture_output=True, text=True, timeout=timeout,
                encoding="utf-8",   # same reason, for what comes back
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(ok=False, stdout="", stderr="timeout", timed_out=True)
    finally:
        os.unlink(f.name)  # always delete, even on timeout or unexpected exception
    return SandboxResult(
        ok=(proc.returncode == 0), stdout=proc.stdout, stderr=proc.stderr,
        timed_out=False,
    )
