# Security design and limits

The operator chooses executable paths, policy and roots. Agents supply only
four bounded tool contracts. Remote titles, descriptions and subtitles are
adversarial data; the shared Python core enforces policy for every adapter.

```text
Operator policy / local approval
                 |
Agent -> MCP / native DSH -> validation, approvals, state lock
                                      |
                         short-lived guarded yt-dlp worker
                                      |
                         HTTPS / public IP -> remote CDN

Remote text -> bounded escaped JSON data -> model/user
              (never instructions or approval)
```

| Threat | Implemented control | Evidence |
|---|---|---|
| Shell/argument injection | Fixed argument arrays, stdin JSON, no shell/raw options | CLI/DSH malformed-input tests |
| Prompt hijacking/role spoofing | Field allowlist, trust envelope, bounded text, Skill data/authority separation; no approval/config tool | Metadata/subtitle fixtures; independent skill review |
| XML/XXE/control injection | Escape markup/quotes, strip controls/bidi; no XML parsing or instruction-template interpolation | XML/control fixtures |
| SSRF/redirect/DNS rebinding | HTTPS requests, entry allowlist, every actual Python socket checks resolved global IP and port443; urllib-only transport | Private redirects, rebinding, IPv6/private/multicast tests |
| Unapproved/replayed download | Default off; immutable-plan SHA-256, policy fingerprint, TTL, consume before network | Missing/modified/expired/replayed/failure tests |
| Concurrency amplification | Per-plan exclusive lock and one worker per shared state root | Concurrent-consumer/global-slot tests |
| Path traversal/overwrites | UUID destination, fixed media basename/extension, link/reparse rejection, exclusive creation | Identifier/filename/symlink tests |
| Host config/plugins/credentials | Python API in -I process, no user config loader; plugins disabled before import; no cookies/netrc/proxy inheritance | Fixed options, isolated worker integration |
| Processing command execution | JS/remote components/FFmpeg/postprocessors disabled; worker denies subprocess creation | Process-denial fixture; direct HTTPS format selection |
| Resource exhaustion | Default90s/max180s; media50MiB/max200MiB; subtitle1MiB/max2MiB; text20k/max50k; output512KiB/stderr64KiB; metadata network4MiB, download media+4MiB | Budget, compression, progress and cancellation tests |
| Compression/error-body bombs | Identity encoding; reject compression and wrap byte budget before yt-dlp decompression/error processing | gzip/deflate/br and error-body regressions |
| Leaking upstream data | Minimal worker environment; curated results/errors; no signed media URLs, headers or raw upstream errors returned | Result/error contracts |
| Orphans/memory | Windows kill-on-close Job Object; Linux parent-death SIGKILL;512MiB worker memory on Windows/Linux; kill+wait on cancellation | Running-worker termination test; platform CI |
| Supply chain/drift | Exact dependencies, lockfiles, ignore-scripts; canonical skill/schema synchronization check | Frozen installs and packaging checks |

## Remaining risks

1. Escaping prevents literal markup boundary breaks, not all semantic prompt
   attacks. Models may still obey encoded/plain language attacks. Host tool
   permissions and provenance remain necessary; the skill forbids self-approval.
2. Same OS account means one trust domain. Unrestricted agents can forge state,
   replace executables or run raw tools. Use separate identities/ACLs and an OS
   sandbox when defending against a compromised agent. This package does not
   claim to install such isolation or modify application permissions.
3. Existing-link checks are not race-proof against a hostile local process
   already allowed to mutate parent directories. Restrict directory ACLs.
4. IP checking covers the pinned Python/urllib path, not kernel egress or all
   public destinations. TUN/gateway routing can rewrite traffic afterward.
   Local proxy/fake-IP environments fail closed; no network config is changed.
5. Downloader hooks and 50ms supervision may observe a small disk overshoot
   before termination. Exact quotas need OS controls. A crash can leave bounded
   temp data and a stale lock; recovery is explicit and never age-based.
6. Some sites need JS challenges, compressed responses, login, manifests or
   FFmpeg. Such paths are rejected, not silently enabled. The 720p filter applies
   only to known metadata; direct files with missing codec/resolution metadata
   may be accepted under the same byte/protocol limits. Resolution is not an
   independently measured security guarantee, and downloaded media is not decoded.
7. macOS has normal kill+wait but lacks the implemented Windows/Linux memory
   and parent-death controls. It is an installation path, not a verified strong
   isolation target; validated target platforms are Windows and Linux.
8. MCP annotations are behavior hints, not permissions. Plan creation writes
   state. Clients must enforce actual permissions. No implicit network/upload,
   Cookie extraction or configuration mutation is authorized by tool output.

Green tests do not prove arbitrary websites, host profiles, networks or future
dependency versions safe and compatible.
