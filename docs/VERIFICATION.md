# Verification record

The checked-in tests cover observable behavior, not a promise of no bugs.
Versions are pinned in uv.lock and adapters/dsh/package-lock.json.

Initial dependency auditing identified known issues in MCP SDK 1.28.0. The
runtime pin was upgraded to 1.30.0; the 31-test Python suite passes with that
version. The fully hashed locked dependency audit and npm production audit
report no known vulnerabilities at the validation time. This is a database
snapshot, not proof that undiscovered issues do not exist.

Local checks cover strict inputs, XML/control characters, connection-time
guards, redirects/rebinding, immutable approvals, expiry/replay/failure,
concurrency, paths and running-worker cancellation. A real stdio MCP client
negotiates, lists tools and exercises plan/denial behavior. Real yt-dlp runs
against deterministic transport fixtures for metadata, subtitles, video/audio
selection and downloads; these tests make no external requests.

An initial Linux CI external probe retrieved the W3C fixture metadata but
rejected its download because the bare media response lacks codec/resolution
metadata. That case was reproduced with the real Generic extractor and fixed:
unknown metadata is allowed under the same HTTPS/container/byte limits, while
known resolutions above 720p remain excluded. A regression covers this case.

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

On the initial Windows machine, the external metadata probe was blocked because
DNS resolved the fixture to reserved fake-IP range 198.18.0.0/15. This proves
fail-closed behavior, not successful external downloading. No network settings
were changed. Live YouTube/Bilibili/Vimeo compatibility remains site-dependent.

No paid model calls, browser credentials or live user-profile changes were
used. Full authenticated model conversations in each host are not proven by
manifest/registry/protocol tests. CI validates Windows/Linux fixtures and
packaging and known-dependency audits; consult actual workflow results. An explicit workflow-dispatch flag
can request the fixed public smoke test separately.
