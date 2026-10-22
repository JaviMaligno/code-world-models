# Security environment and historical provenance

`docs/paper2/requirements-frozen.txt` records the environment captured for the
historical paper. It remains unchanged. It is not a hashed lock and is not the
recommended environment for processing new, untrusted inputs.

`requirements/paper2-security.in` is a separate security alternative derived from
that capture. Only AnyIO changes from 4.14.0 to 4.14.2 and certifi from 2026.6.17 to
2026.10.19. The `cwm==0.1.0` line is omitted because the application must come from
this checkout, rather than a namesake package resolved from PyPI. The compiled
`requirements/paper2-security.txt` includes hashes and was resolved for Linux and
Python 3.12. No experiment or paper claim has been rerun or revalidated under it.

From the repository root, with uv 0.13.5:

```sh
uv venv --python 3.12.15 .venv-paper2-security
uv pip sync --python .venv-paper2-security/bin/python --require-hashes requirements/paper2-security.txt
uv pip install --python .venv-paper2-security/bin/python --no-deps -e .
```

On Windows, use `.venv-paper2-security/Scripts/python.exe` instead. The final
command builds the local project in an isolated build environment; it does not
re-resolve its runtime dependencies. None of these commands launches experiments.

For fresh development/CI installations, `requirements/runtime-security.txt`
constrains the two affected network trust/runtime packages without replacing the
historical capture or forcing its other scientific package versions. CI bootstraps
pip 26.2.2 from a hash-verified wheel before dependency installation. Draft PRs run
syntax checks; full Python, paper and proof checks run after Ready. Hosted CI and
separate compatibility checks are still required before readiness is claimed.
