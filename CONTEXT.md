# Project Context

## Current Brief

Objective: a reusable yt-dlp tool and skills package for DeepSeek Harness (DSH,
native plugin), Codex and Claude Code, with a complete manual, project tree,
executable security controls, tests and a public source repository.

Scope: public single-video metadata, subtitles, bounded media downloads;
shared Python core, CLI, stdio MCP, native DSH plugin and reusable skills.
No guarantee of zero bugs or immunity to prompt injection is possible.

Active Authorization:
- Target: new local `yt-dlp-agent-kit` project and new public repository of the
  same name under the currently authenticated GitHub account.
- Permitted: implementation, scoped dependency installation in this project,
  tests, isolated adapter validation, documentation, Git commits and publication.
- Boundary: local CPU/network and standard free public GitHub CI, no paid APIs or media upload; public tests
  use a fixed public W3C trailer fixture, at most one <=5 MiB media download.
- Prohibited: modifying existing TTS assets or live agent settings, reading
  browser credentials/cookies, publishing local paths/logs/secrets or unrelated
  files, npm/PyPI publication, external messages, paid infrastructure.
- Completion: tests and packaging pass; all three adapters are evidenced;
  manual/tree/security limitations accurate; public Git source verified.
- Stop: new login challenge, missing permission, unknown destructive target,
  unexpected secrets, a dependency requiring unsafe install hooks, or resource
  expansion. Preserve state and report any unverified requirement.

## Decisions and Contracts

- DSH means DeepSeek Harness, confirmed directly by the user.
- Use native DSH tools, not a DSH MCP-only workaround.
- Keep one shared core; do not implement site extraction independently.
- Download plans need out-of-band local approval and one-time consumption;
  tool arguments cannot grant approval. Skills do not change host permissions.
- Public source only; no changes in the existing TTS workspace.
- Root owns this file. Superrouter direct execution; independent review only
  after the implementation is concrete.

## Verification and Remaining Risk

Initial discovery: original workspace is unrelated TTS content and is not a Git
repository. New project initialized separately. No relevant historical memory
found; OpenViking returned unrelated projects. Official current DSH, Codex,
Claude Code and yt-dlp documentation inspected. Local DSH executable absent;
Node, Python, uv, Codex CLI and Claude Code CLI available.

## Pending List

- [x] Implement strict shared policy, bounded worker, plans/approval and CLI.
- [x] Implement stdio MCP and native DSH bundle; package common skills.
- [x] Verify malicious inputs, output escaping, paths, approval/replay,
      concurrency, timeouts, cancellation and protocol behavior.
- [x] Verify adapter loaders/registries using isolated configuration.
- [x] Write README/manual/tree/security model and reproducible install steps.
- [x] Independent behavioral/security review and justified fixes.
- [ ] Package, publish clean public repository and verify remote state/CI.

## Exact Next Action

Package, review publication contents, create/push the public repository and verify CI.

Local milestone: 30 Python tests and 4 DSH tests passed; wheel/sdist and DSH
tarball build; native Claude manifests validate without warnings; Skill Creator
validation passes; Codex local marketplace discovery verified in isolated config.
Independent review found response-bound and cached audio-selector defects,
both fixed with real yt-dlp regression fixtures. A running-worker cancellation
and single global worker slot are now tested. External Windows fixture probe
is blocked by reserved fake-IP DNS; no network setting changed. Only local
fixture acceptance is claimed until a standard public CI live probe succeeds.

Public repository created and main pushed. Initial Windows/Linux CI passed.
Dependency audit then found MCP 1.28.0 advisories; upgraded to 1.30.0, reran
31 Python tests, hashed-lock audit now reports no known vulnerabilities.
Audit added to CI. Native DSH npm production audit also clean. Final CI and
one bounded public fixture download are next; no local network relaxation.

Latest evidence: upgraded-dependency Windows/Linux CI passed. First Linux
external probe retrieved metadata but failed direct-file format selection;
no completed media download. Reproduced missing codec/resolution metadata in
the actual Generic extractor, fixed optional metadata selection, added test31.
Known >720p remains excluded; unknown resolution is documented rather than
claimed verified. HEAD verification then established the bunny fixture is
11,053,871 bytes, above the existing 5MiB cap; denial is expected. The same
provider's Sintel fixture is 4,372,373 bytes by HEAD, within the unchanged cap.
Use that fixed sample for the one normal live download; no cap increase.
