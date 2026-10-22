# Security

Read [the security design](docs/SECURITY-DESIGN.md) before exposing these tools.
No claim of zero bugs, universal prompt-injection prevention or OS sandboxing
is made. Downloads default off; no approval/configuration/shell tool is exposed.

Report non-sensitive defects with a minimal reproducer and versions. For an
exploitable issue, use GitHub private vulnerability reporting when available;
never post secrets, cookies, signed URLs, private media or personal paths.
If private reporting is unavailable, open only a redacted request for a private
contact channel. Do not test exploits against another user's host.

Version 0.1.x is in scope for fixes. Review dependency updates before installing;
pin commits/lockfiles and disable npm lifecycle scripts.
