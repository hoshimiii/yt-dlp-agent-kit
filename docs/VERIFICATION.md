# Verification record

The checked-in tests cover observable behavior, not a promise of no bugs.
Versions are pinned in uv.lock and adapters/dsh/package-lock.json.

Validation snapshot: 2026-10-22. The 33-test Python suite and four native DSH
tests pass. Runtime dependencies pin MCP SDK 1.30.0 and yt-dlp 2026.10.21.
The built wheel was installed into a separate environment and all 33 Python
tests passed there. Windows and Linux job logs for
[source validation](https://github.com/hoshimiii/yt-dlp-agent-kit/actions/runs/39796090923)
also record 33 Python tests, four DSH tests and successful package builds.
The fully hashed locked dependency audit and npm production audit report no
known vulnerabilities at the validation time. This is a database snapshot,
not proof that undiscovered issues do not exist.

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
Python bridge. Codex CLI marketplace discovery is checked with isolated
configuration. Claude Code validates native plugin/marketplace manifests.
Skill Creator validates the skill structure. Independent read-only review found
response-budget and audio-selection defects; regression tests cover the fixes.

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

No paid model calls, browser credentials or live user-profile changes were
used. Full authenticated model conversations in each host are not proven by
manifest/registry/protocol tests. CI validates Windows/Linux fixtures and
packaging and known-dependency audits; consult the
[actual workflow results](https://github.com/hoshimiii/yt-dlp-agent-kit/actions/workflows/ci.yml).
The fixed public smoke test remains opt-in through workflow dispatch; site-access
denials must be reported rather than bypassed.
