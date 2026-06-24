"""Tests for the sandbox executor."""
from cwm.sandbox import run_in_sandbox

def test_runs_and_captures_stdout():
    r = run_in_sandbox("def f():\n    return 3\n", "print(f() + 4)")
    assert r.ok is True and r.stdout.strip() == "7" and r.timed_out is False

def test_captures_error():
    r = run_in_sandbox("def f():\n    raise ValueError('boom')\n", "f()")
    assert r.ok is False and "ValueError" in r.stderr and "boom" in r.stderr

def test_times_out():
    r = run_in_sandbox("import time\n", "time.sleep(10)", timeout=1.0)
    assert r.timed_out is True and r.ok is False
