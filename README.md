# project-manager-archetype

The **Project Manager** archetype bundle for [protoAgent](https://github.com/protoLabsAI/protoAgent) —
a single-repo project manager that reads deeply but never holds the keyboard:
work is decomposed into board features, dispatched to a coding agent in a
disposable git worktree, opened as a PR, passed through a **blocking adversarial
review gate**, and reported as it merges to done. The project-team counterpart
of the Portfolio Manager (portfolio-manager-archetype).

This repo is also the **reference bundle**: it exercises every part of the
bundle/archetype contract — pinned members, recommended config, create-time
`config_inputs`, the `archetype:` block, the capability contract, and the
verify-and-bump pin lifecycle. If you're authoring a bundle, copy its shapes.

## What's inside

| plugin | source | role |
|---|---|---|
| `delegates` | builtin | ACP/A2A spawn spine — the coding agents, plus `propose_delegate` (consent-gated registration when the roster is empty) |
| `workflows` | builtin | the review gate's **runner** + the bundled `code-review` recipe (parallel finders → synthesizer → verifier) |
| `friction` | builtin | write-only harness-friction ledger — every tool exception leaves evidence instead of vanishing |
| `project_board` | [projectBoard-plugin](https://github.com/protoLabsAI/projectBoard-plugin) | the board + spawn loop: features → worktree builds → PRs → review gate → done; live coder monitor |
| `agent_browser` | [agent-browser-plugin](https://github.com/protoLabsAI/agent-browser-plugin) | a real browser to verify running changes |
| `github` | [github-plugin](https://github.com/protoLabsAI/github-plugin) | issues/PR rail — write ON (the persona files the pain points it finds); the loop merges its own reviewed, CI-green PRs when `auto_merge` is on, otherwise a human does |

The setup-gap banner (core ≥ 0.146) is the floor for seeing these plugins'
preflight in the console; on older cores they only log. The config defaults enforce the archetype's core invariant — **the lead reads,
the pipeline writes**: file-mutation tools are disabled (`tools.disabled`),
investigation tools stay, every change ships as a reviewed PR, and `edit_soul`
history is on so persona evolution stays reversible.

## Install

```
python -m server plugin install https://github.com/protoLabsAI/project-manager-archetype
```

— or pick **Project Manager** in the new-agent picker; it installs this bundle.

## Before you start

Two host binaries the Configure step cannot install for you, both on the PATH the
agent process sees (the desktop app passes your login-shell PATH; launchd
autostart / Linux hosts may need an absolute `command:` on the delegate):

* **`br`** — beads-rust. projectBoard ≥ 0.43.0 fetches a pinned build itself on
  first run (`project_board.br_autofetch`, on by default; needs github.com
  reachable); otherwise `cargo install beads_rust` (*not* the homebrew `bd`).
  The board is a projection over beads; without it the board is paused.
* **`gh`** — the GitHub CLI, logged in (`gh auth login`) or a token pasted in
  Settings ▸ GitHub (github-plugin ≥ 0.6.0). Issues, PRs, and the loop's merge
  edge all ride it.

When either is missing the member does **not** boot green: it raises an operator
warning (core ≥ 0.146, the plugin setup-gap seam) and the board's setup card
names the gap; projectBoard ≥ 0.42.0 pauses the loop with the reason and resumes
by itself once the binary appears.

## First run: asked, not discovered

On core ≥ 0.144.0 the create flow renders this manifest's `config_inputs:` as a
Configure step — five answers, written into the agent's config:

| answer | key | notes |
|---|---|---|
| the repo this board manages | `project_board.repo` | **required**; on core ≥ 0.146 also registered as a managed project (ADR 0095 `projects:` entry, GitHub `owner/name` from its origin remote, `onboarding.root` scoped to its parent) |
| the coder delegate | `project_board.coder` | **required**; a dropdown of the host's coding (`acp`) delegates — on core ≥ 0.146 the picked entry is *copied* into the new member's own registry |
| the GitHub repo | `github.default_repo` | `owner/name` for issues/PRs (github-plugin ≥ 0.6.0 derives it from the repo's remote when blank) |
| start the loop now | `project_board.loop_enabled` | off by default — a loop with no repo or coder can only thrash |
| merge reviewed PRs itself | `project_board.auto_merge` | **on** by default: a reviewed, CI-green PR merges and the card reaches *done* without a human; off means *you* merge and the card waits in *in_review* |

On core ≥ 0.146 the two required answers are a hard gate — a create without
them is refused, naming the prompt. What the form still can't conjure:

1. **A coder delegate must exist on the host.** If the dropdown says "No coding
   (acp) delegates configured": register one in Settings ▸ Delegates, or let the
   agent `propose_delegate` (core ≥ 0.145) — it validates + probes the entry and
   pauses for your approval; nothing registers without it.
2. **Grounding.** The Configure-step repo is already a managed project; the
   persona reads it through the registry (its grounding doc, ADRs, gate table).
   projectBoard's `onboard-project` skill declares the local gate command and
   writes the grounding doc when the repo has none.

## The review gate

`review_gate: true` ships **runnable**: the `workflows` member provides the
runner and the bundled `code-review` recipe, so a PR only settles into review
after a clean adversarial pass; blocking findings bounce back to the coder
(bounded by `review_fix_max`). The gate fails **closed** — if it can't run, the
card blocks with the reason on it rather than silently degrading to advisory.
A boot warning about the workflows `config_section` colliding with a built-in
is benign.

## Pin lifecycle (ADR 0049)

Members pin release **tags**. On core ≥ 0.146 a release-tag pin is a **floor**,
not the answer: a fresh install (and a bundle update) takes each member's newest
semver tag, so a member the operator force-installed ahead of the archetype is
never downgraded and a new plugin release reaches new agents without waiting for
a pin bump (protoAgent #2960). `python -m server plugin update-bundle
project-manager-archetype` on a member does the same — it moves the bundle to
its newest tag and each member to theirs; pass `--ref` only to pin. The pin
still records what was *verified*, and the bump PR is how that record moves:
`scripts/check_bundle_updates.py` proposes bumps (weekly + on demand),
`.github/workflows/verify-bundle.yml` installs the pin set into a scratch agent
on a fresh protoAgent checkout and probes every declared console view. A pin-bump
PR that fails verify doesn't merge. Keep member entries on ONE line — the
checker rewrites `ref:` in place.
