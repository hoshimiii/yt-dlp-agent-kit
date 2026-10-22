# Project Context

## Current Brief

Objective: complete five sequential user-driven improvement rounds on the
existing yt-dlp tools for native DSH, Codex and Claude Code. Astra performs
isolated user tests, root records requirements/proposals, Astra and the Sol
architect review each proposal, and implementation is retested before its
version-control checkpoint. Completed as v0.2.0; root is the sole writer of this file.

Active Authorization:
- Target: existing yt-dlp-agent-kit project/repository; baseline main 6b9aa0e,
  working branch feat/v0.2.0-iterations. Existing v0.1.0 tag remains immutable.
- Permitted: scoped edits, project-only dependency installs/tests, isolated
  adapter validation, Git management, public source/packages and standard free
  public GitHub CI. Native Astra user testing and Sol architecture review,
  scoped implementation, regression checks, five round commits and a final
  versioned package are authorized. Local fixtures are the acceptance baseline.
- User correction: finish all five local iterations, root code-quality review,
  complete tests and artifact validation BEFORE the next push. No intermediate
  pushes or GitHub external-site debugging. Existing remote R1 CI 39804781364
  passed; earlier failure notifications came from manual external probes.
- Prohibited: changing original TTS assets or live agent settings, reading
  browser credentials/cookies, media upload, secrets/private paths in public
  artifacts, third-party paid APIs/infrastructure, npm/PyPI publication, external messages,
  DNS/TUN/proxy/route modifications or relaxing safety to pass a test.
- Completion: five distinct rounds with observed user needs, recorded scope and
  design, joint user/architect review, implementation and retest evidence;
  coherent version/package/docs and clean remote version control. Never claim
  zero bugs, absolute injection immunity or an OS sandbox. Full authenticated
  host conversations are outside these isolated tests.
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

- Current v0.2.0: root inspected all five diffs; new independent Sol aggregate
  review ACCEPT with cross-Service replay/admission/failure check. Source and
  final installed Windows/Linux wheel each passed51Python and DSH5; installed
  dependencies are compatible. Astra final cross-entry built-package flow PASS.
  Python hashed audit/npm full audit clean; skill/assets/Claude manifests pass.
- Final Linux gate completed after host resources improved from a transient
  WSL HCS/ERROR_NO_SYSTEM_RESOURCES cold-start failure. One scoped retry passed;
  no system settings/unrelated processes changed and no acceptance was lowered.
- Wheel/source/DSH content and absence of caches/state checked, SHA-256 sums
  generated. Local pre-push quality gate is complete; no media probe was rerun.
- Final-local-gate checkpoint saved; the Superrouter native compression reminder
  helper was launched once. Work continued without waiting for compaction.
- Release v0.2.0 targets d7bd2fa. Main CI 39812544729 and iteration-branch CI
  39812544410 passed both platforms. Published wheel/source/DSH attachments were
  downloaded again and verified byte-for-byte and against SHA256SUMS.
- Baseline v0.1.0 evidence below is historical, not final v0.2.0 acceptance:
- 33 Python tests pass from the final installed wheel in a separate environment.
- Four native DSH tests passed: actual registries, disposal and Python bridge.
- Claude native plugin/marketplace validation passes; Codex local marketplace
  discovery verified in isolated configuration; Skill Creator validator passes.
- Windows/Linux job logs for release source 3735b94 (run 39797014123) record 33 Python
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
- Public prerelease v0.1.0 targets 3735b94. Published wheel, source archive and
  native DSH tarball were downloaded again and compared byte-for-byte and via
  SHA-256 with the inspected artifacts. No npm/PyPI publication was performed.

## Pending List

- [x] Round 1: worker busy preserves approval; joint review, implementation,
      independent retest; 36 Python and four DSH tests pass.
- [x] Round 2: valid repeat approval idempotent; joint review and independent
      CLI/read-only/anomaly retest pass; 40 Python tests pass. R1 bbfe7b3.
- [x] Round 3: supported manual/automatic selection; both reviews/retest pass,
      root44Python pass and test fixture reviewed; local-only. R2 c0dc3c2.
- [x] Round 4: safe missing-policy errors/MCP initialization boundary; joint
      review and three-entry independent retest pass; root48Python/5DSH pass.
- [x] Round 5: validated show-plan limit/switch fields; both reviews and
      independent CLI retest pass; root50Python pass. No model tool added.
- [x] Final package/version/docs and full local Windows/Linux quality gate.
- [x] Unified push, ordinary CI, versioned release and public artifact verification.

Requirements, joint reviews and bounded acceptance evidence are recorded in
docs/ITERATIONS.md. Source v0.1.0 verification above is baseline evidence, not
proof of the five new rounds. OpenViking lookup returned no relevant project
record; current repository evidence is authoritative.

## Exact Next Action

None. Five rounds, local acceptance, ordinary CI and public release verification
are complete. No live host profile was changed, no media probe rerun, and no
background work/monitoring is scheduled. Further installation or feature work
requires a new user request within the existing safety boundaries.
