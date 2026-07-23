# project-manager-stack

The **Project Manager** archetype bundle for [protoAgent](https://github.com/protoLabsAI/protoAgent) —
a single-repo project manager that reads deeply but never holds the keyboard:
every change ships through a board of coding agents, verdict-gated, reported as
it merges. The project-team counterpart of the Portfolio Manager (pm-stack).

| plugin | source | role |
|---|---|---|
| `delegates` | builtin | ACP/A2A spawn spine — the coding agents |
| `project_board` | [projectBoard-plugin](https://github.com/protoLabsAI/projectBoard-plugin) | the board + spawn loop: features → worktree builds → PRs → done |
| `agent_browser` | [agent-browser-plugin](https://github.com/protoLabsAI/agent-browser-plugin) | a real browser to verify running changes |
| `github` | [github-plugin](https://github.com/protoLabsAI/github-plugin) | read-only issues/PRs rail (writes stay with the operator + coders) |

The config defaults enforce the archetype's core invariant — **the lead reads,
the pipeline writes**: file-mutation tools are disabled (`tools.disabled`),
investigation tools stay, and `edit_soul` history is on so persona evolution
stays reversible.

## Install

```
python -m server plugin install https://github.com/protoLabsAI/project-manager-stack
```

— or pick **Project Manager** in the new-agent picker; it installs this bundle.

## After install (required)

1. **Register a coder delegate** (Settings ▸ Delegates) — the bundle ships NO
   coder binding; coding agents are host-installed binaries. Use ABSOLUTE
   command paths (GUI hosts don't inherit your shell PATH). Then set
   `project_board.coder` (or a `coders:` tier ladder) to its name.
2. **Bind the repo** — run the `onboard-project` skill: it scans the repo,
   declares the local gate command, and writes the grounding doc. Pin
   `project_board.db_path` to a private store if the target repo commits its
   own `.beads/`.

Pins move through release tags only (ADR 0049) — `scripts/check_bundle_updates.py`
proposes bumps, `.github/workflows/verify-bundle.yml` gates them.
