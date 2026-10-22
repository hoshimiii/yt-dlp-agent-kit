# Verification record

The checked-in tests cover observable behavior, not a promise of no bugs.
Versions are pinned in uv.lock and adapters/dsh/package-lock.json.

Validation snapshot: 2026-10-23, v0.2.0. All five user-driven rounds
have joint proposal review and independent retest evidence in
[ITERATIONS.md](ITERATIONS.md). The complete local gate below passed before the
next push; GitHub was not used to debug these iterations.

| Check | Result |
|---|---|
| Windows Python 3.13.2, source environment | 51 tests passed |
| Same final wheel installed in separate Windows environment | 51 Python tests and five native DSH tests passed; dependency consistency passed |
| Same final wheel on Ubuntu 24.04 / Python 3.12.3 | 51 Python and five native DSH tests passed; dependency consistency passed |
| Fresh independent Sol review of combined runtime/version changes | ACCEPT; cross-Service contention/idempotence/failure/replay fixture passed |
| Final packaged user workflow, Astra | PASS: real MCP -> CLI inspect/approve twice -> injected offline runner consumes once -> replay denied; packaged DSH bridge shares policy/state |
| Locked Python audit / full npm audit | No known vulnerabilities reported |
| Skill, asset synchronization, Claude plugin/marketplace, Python compilation | Passed |
| Wheel, source archive and DSH tarball | Inspected contents match build source; no local cache/state; SHA-256 sums generated |

Runtime dependencies remain MCP SDK 1.30.0 and yt-dlp 2026.10.21; only the
project version changed in lockfiles. Audits are a database snapshot, not proof
that undiscovered issues do not exist. A WSL cold start initially failed with
HCS/ERROR_NO_SYSTEM_RESOURCES. After local test processes ended and host resources
improved, one scoped retry completed the final Linux gate. No system configuration,
network policy or unrelated process was changed to force it.

Local checks cover strict inputs, XML/control characters, connection-time
guards, redirects/rebinding, immutable approvals, expiry/replay/failure,
concurrency, paths and running-worker cancellation. A real stdio MCP client
negotiates, lists tools and exercises plan/denial behavior. Real yt-dlp runs
against deterministic transport fixtures for metadata, subtitles, video/audio
selection and downloads; these tests make no external requests.

The real Generic extractor is tested with bare media lacking codec/resolution
metadata: unknown metadata is allowed under the same HTTPS/container/byte limits,
while known resolutions above 720p remain excluded. A regression covers this case.

HTTP byte bounds instrument the original response's read methods, preserving its
standard-library type. A real urllib/yt-dlp synthetic 403 regression verifies both
status translation and the bounded error body. Worker failures expose safe error
categories rather than raw upstream messages, URLs or remote instructions.

Native DSH tests load actual Cordis ToolRuntime and SkillRegistry, register all
four tools and a packaged skill, verify disposal and invoke the installed
Python bridge. The final packaged workflow verifies wheel identity/version and
calls the original bridge bytes from the final DSH tarball. Version regressions
check Python distribution/runtime, both lockfiles, client manifests and MCP
handshake consistency. Codex marketplace discovery was verified in isolated
configuration for v0.1.0; v0.2.0 retains the layout and tests its manifest version.
Claude Code validates the current native plugin/marketplace manifests. Skill
Creator validates the current skill structure. These are bounded integration
checks rather than complete authenticated host conversations.

## External acceptance

scripts/smoke_live.py probes one fixed public W3C media URL. --download permits
one <=5MiB download and records evidence only in ignored .cache/live/. It never
runs during installation.

On the Windows machine, the external metadata probe was blocked because
DNS resolved the fixture to reserved fake-IP range 198.18.0.0/15. This proves
fail-closed behavior, not successful external downloading. No network settings
were changed.

The explicit Linux CI probe retrieved real W3C metadata, but the Sintel media
endpoint returned HTTP 403 / a Cloudflare anti-bot challenge. See the
[bounded external probe and fixed-URL diagnostic](https://github.com/hoshimiii/yt-dlp-agent-kit/actions/runs/39796092239).
That probe was stopped without impersonation, cookies, IP/TLS policy changes or
further access attempts. No successful live media download is claimed.
Live YouTube/Bilibili/Vimeo compatibility remains site-dependent.

Native Astra/Sol review runs were explicitly requested. No third-party paid
API, browser credentials or live user-profile changes were used. Full
authenticated model conversations in each host are not proven by
manifest/registry/protocol tests. CI validates Windows/Linux fixtures and
packaging and known-dependency audits; consult the
[actual workflow results](https://github.com/hoshimiii/yt-dlp-agent-kit/actions/workflows/ci.yml).
The fixed public smoke test remains opt-in through workflow dispatch; site-access
denials must be reported rather than bypassed. It was not rerun for this iteration.
Local complete review/test/package gates precede the next push; GitHub Actions
is not used for repeated external-availability debugging.
