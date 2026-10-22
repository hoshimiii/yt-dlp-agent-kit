# Project Context

## Current Brief

Objective: reusable yt-dlp tools and skills for DeepSeek Harness (native DSH
bundle), Codex and Claude Code, with a complete manual/tree, executable risk
controls, tests and a public repository. Root is the sole writer of this file.

Active Authorization:
- Target: yt-dlp-agent-kit local project and its new public GitHub repository.
- Permitted: scoped edits, project-only dependency installs/tests, isolated
  adapter validation, Git management, public source/packages and standard free
  public GitHub CI. One normal fixed W3C media download, <=5MiB, is permitted.
- Prohibited: changing original TTS assets or live agent settings, reading
  browser credentials/cookies, media upload, secrets/private paths in public
  artifacts, paid models/infrastructure, npm/PyPI publication, external messages,
  DNS/TUN/proxy/route modifications or relaxing safety to pass a test.
- Completion: source/package integrity, core and three adapters evidenced,
  accurate manual/tree/security limits, independent review, verified public
  source and CI. Never claim zero bugs, absolute injection immunity or an OS
  sandbox. Full authenticated host conversations are outside these local tests.
- Stop: new login/permission challenge, unapproved destructive/resource target,
  discovered secrets, unsafe dependency install hooks, or confirmed site-access
  denial. Preserve state; do not repeat unchanged failures or bypass a denial.

## Confirmed Implementation

Four tools: metadata, one VTT/SRT subtitle track, download planning and download.
Python Service owns URL/path validation, approvals, cross-process locks and
worker limits. MCP/JSON CLI/native DSH delegate to it. No model-facing approval,
configuration or shell tool. Downloads default disabled; plans are immutable,
15-minute, operator-approved and consumed once before network access.

Native DSH uses the actual defineTool/ToolRuntime and SkillRegistry contracts.
Codex and Claude package the common skill and stdio MCP; existing live profiles
were not changed. Dependencies are locked; MCP is 1.30.0 after known-advisory
checks. No npm install lifecycle scripts are required.

Known direct formats above720p are excluded; absent codec/resolution metadata
may be accepted under protocol/container/byte bounds. No JS engines, remote
components, FFmpeg, manifests, postprocessors, browser cookies or credentials.

## Verification and Remaining Risk

- 33 Python tests pass from the final installed wheel in a separate environment.
- Four native DSH tests passed: actual registries, disposal and Python bridge.
- Claude native plugin/marketplace validation passes; Codex local marketplace
  discovery verified in isolated configuration; Skill Creator validator passes.
- Windows/Linux job logs for source 2bbbae1 (run 39796090923) record 33 Python
  and four DSH tests, clean known-dependency audits and successful builds.
- Hashed locked Python audit and npm production audit report no known issues at
  check time. This does not prove undiscovered vulnerabilities absent.
- Independent review found response budget, cached audio selection and HTTP
  error identity defects. All have concrete fixes/regressions; a running-worker
  cancellation and a single global worker slot are tested.
- Local external networking fails closed on reserved fake-IP DNS. CI retrieved
  real W3C metadata, then confirmed HTTP 403 / Cloudflare anti-bot challenge for
  the fixed Sintel sample (run 39796092239). Stop condition reached: no further
  requests to that endpoint or policy relaxation. No live download is claimed.
- Site-specific live compatibility, authenticated model conversations and macOS
  isolation are not claimed. Same-account arbitrary shell access remains outside
  this application's security boundary; protect policy/state with host controls.

## Pending List

- [x] Shared core, approval CLI, MCP and native DSH bundle/Skill.
- [x] Manual, project tree, security design, frozen dependencies and packages.
- [x] Local security/protocol/media fixtures and independent review/fixes.
- [x] Public repository created and source pushed.
- [x] Verify Windows/Linux default CI logs for final runtime code.
- [x] Record external probe limitation and stop on confirmed access denial.
- [ ] Reconcile final verification/state, build exact release artifacts,
      publish a source/package release and verify hashes/remote contents.

## Exact Next Action

Build final wheel/sdist/native DSH tarball, run the suite against the installed
wheel, inspect exact packaged files, and publish a versioned GitHub release with
SHA-256 sums. Verify final default CI and public remote contents. Do not restart
the external probe or repeat checks without a changed artifact or open concern.
