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
| `github` | [github-plugin](https://github.com/protoLabsAI/github-plugin) | issues/PR rail — write ON (the persona files the pain points it finds); merges stay human |

The config defaults enforce the archetype's core invariant — **the lead reads,
the pipeline writes**: file-mutation tools are disabled (`tools.disabled`),
investigation tools stay, every change ships as a reviewed PR, and `edit_soul`
history is on so persona evolution stays reversible.

## Install

```
python -m server plugin install https://github.com/protoLabsAI/project-manager-archetype
```

— or pick **Project Manager** in the new-agent picker; it installs this bundle.

## First run: asked, not discovered

On core ≥ 0.144.0 the create flow renders this manifest's `config_inputs:` as a
Configure step — the board repo, the coder delegate (a dropdown of the host's
registered ACP delegates), the GitHub repo, and the loop toggle are collected
up front and written into the agent's config — plus **whether the loop merges its
own PRs** (`project_board.auto_merge`, on by default here: a reviewed, CI-green PR
merges and the card reaches *done* without a human; off means *you* merge, and the
card waits in *in_review* until you do). Two things the form can't conjure:

1. **A coder delegate must exist on the host.** Coding agents are host-installed
   binaries (absolute command paths — GUI hosts don't inherit your shell PATH).
   If the dropdown says "No delegates configured": register one in
   Settings ▸ Delegates, or let the agent `propose_delegate` (core ≥ 0.145) —
   it validates + probes the entry and pauses for your approval; nothing
   registers without it.
2. **Grounding.** Have the agent run `onboard_project` on first contact: it
   scans the bound repo, declares the local gate command, registers the repo in
   the managed-projects registry (filesystem tools, the GitHub picker, and the
   board all read it), and writes the grounding doc. Needs the host's
   `onboarding.enabled` + `onboarding.root` consent gate.

## The review gate

`review_gate: true` ships **runnable**: the `workflows` member provides the
runner and the bundled `code-review` recipe, so a PR only settles into review
after a clean adversarial pass; blocking findings bounce back to the coder
(bounded by `review_fix_max`). The gate fails **closed** — if it can't run, the
card blocks with the reason on it rather than silently degrading to advisory.
A boot warning about the workflows `config_section` colliding with a built-in
is benign.

## Pin lifecycle (ADR 0049)

Members pin release **tags** and only move through a passing verify:
`scripts/check_bundle_updates.py` proposes bumps (weekly + on demand),
`.github/workflows/verify-bundle.yml` installs the pin set into a scratch agent
on a fresh protoAgent checkout and probes every declared console view. A pin-bump
PR that fails verify doesn't merge. Keep member entries on ONE line — the
checker rewrites `ref:` in place.
