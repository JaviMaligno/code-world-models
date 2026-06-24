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
    f = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False)
    try:
        f.write(source)
        f.flush()
        f.close()  # close before the subprocess opens it (also required on Windows)
        try:
            proc = subprocess.run(
                [sys.executable, "-I", f.name],   # -I: isolated, ignore env & user site
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(ok=False, stdout="", stderr="timeout", timed_out=True)
    finally:
        os.unlink(f.name)  # always delete, even on timeout or unexpected exception
    return SandboxResult(
        ok=(proc.returncode == 0), stdout=proc.stdout, stderr=proc.stderr,
        timed_out=False,
    )
