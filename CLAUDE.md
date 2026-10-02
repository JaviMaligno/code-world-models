@AGENTS.md

## Claude Code extras

- Repo skill: `.claude/skills/paper-claims/` — invoke it before reviewing or editing any paper.
- `.claude/hooks/session-start.sh` (SessionStart) installs TeX Live and `pip install -e ".[dev]"`
  only in remote/web sessions (`CLAUDE_CODE_REMOTE=true`); it is a no-op locally.
