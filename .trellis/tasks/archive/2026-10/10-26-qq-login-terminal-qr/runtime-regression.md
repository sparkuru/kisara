# Bug analysis: saved PNG rejected during real login

## 1. Root cause category

- B / Cross-layer contract: a Docker timestamp was treated as ordinary log
  text, redacted, then reused as structured input for PNG freshness checks and
  snapshot/follow deduplication.
- E / Implicit assumption: the Python version accepting timestamp strings in
  development was assumed equivalent to the embedded NapCat runtime.
- D / Coverage gap: reader fixtures executed under hako Python3.12. The prior
  real-PNG probe validated only bitmap rendering and bypassed timestamp parsing.

Two independent discriminating probes established the failures:

1. Public `ONEBOT_EXPORT_MAX_URLS=3` matched the credential classifier's
   `*URL*` wildcard. A synthetic fractional Docker timestamp became
   `.12[redacted]456789Z`; actual CLI snapshot/live cases reached the saved-PNG
   event but failed reading it. A genuine synthetic secret colliding with
   `.314159Z` independently reproduced the same metadata corruption.
2. The cached NapCat image runs Python3.10. In an isolated image probe,
   `datetime.fromisoformat` accepted six-digit fractions and rejected nine-digit
   Docker fractions. The exact pre-fix reader exited with an invalid-event
   category. The repaired reader in that same runtime returned exit0, and
   byte comparison matched the synthetic PNG exactly.

## 2. Why previous checks were insufficient

The PNG geometry, independent decoder and generic CLI tests proved useful
parts of the flow, but not execution of the actual embedded reader with Docker
nanosecond timestamps and timestamp-colliding configuration values. The
`png-unavailable` category also combined timestamp failures with missing files,
making the initial output point at the wrong boundary.

## 3. Prevention mechanisms

| Priority | Mechanism | Specific action | Status |
| --- | --- | --- | --- |
| P0 | Metadata boundary | Preserve validated private Docker timestamps separately from redacted messages; strip before terminal presentation | Independently checked; focused/full gates passed |
| P0 | Runtime compatibility | Parse whole-second date plus integer fractional nanoseconds, preserving freshness bounds on Python3.10 | Actual-image before/after probe passed |
| P0 | Credential semantics | Match actual `_URL` fields, not nonsecret `EXPORT_MAX_URLS` counts | Targeted regression passed |
| P1 | Failure categories | Separate invalid event, missing file, type/size, permission, stale image and timeout/read failure | Independently checked; regression cases passed |
| P1 | Coverage | Exercise snapshot/live collision cases, public counts and the exact reader in the actual cached runtime | Focused62 passed/6 locale skips; full1316 passed/7 skips |

## 4. Systematic expansion

The same timestamp drives both freshness and replay boundaries; fix both with
one structural boundary rather than patching only the reader's ValueError.
Do not weaken message credential redaction to repair control flow. Test the
runtime owning each operation, not only the application's Python wrapper.

At diagnosis time, the default Docker endpoint contained no QQ containers.
No service was started to obtain account evidence. Disposable image probes
used offline/read-only/no-capability execution, synthetic data only and no
account mounts. Bare hexadecimal records were present in earlier user output;
their origin is unconfirmed and no blanket hash suppression was added.

## 5. Knowledge capture

- Updated CLI contracts with private transport metadata, semantic credential
  classification and Python3.10-compatible nanosecond parsing.
- Updated validation guidance to distinguish renderer/format probes from
  actual-runtime reader execution and real phone authorization.
- Preserved prior check history; recorded this reopened acceptance repair and
  its independent verification separately. No template/runtime or commit work
  is authorized by this retrospective.
