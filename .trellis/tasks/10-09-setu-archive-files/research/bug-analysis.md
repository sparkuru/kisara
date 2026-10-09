# Bug analysis: file resolver assumptions hidden by fast mocks

## 1. Root cause categories

- B, cross-layer contract: NapCat file metadata separates original `file`
  basename from canonical `file_id`; Kisara originally selected the basename.
- D, test coverage gap: initial synthetic file tests used only one identifier
  field and returned get_file metadata immediately. They validated archive
  placement but did not establish the actual source-resolution contract.
- E, implicit assumption: get_file was treated like a short lookup, whereas
  installed NapCat waits for full native download. The bot10s deadline and
  native120s deadline are independent.
- B, state deadline interaction: a file save can outlast its60s confirmation
  window; after failure, a retry instruction was unusable without renewing
  that expired file retry transition.

## 2. Why the initial correction was insufficient

Archive naming changes do not repair native file retrieval. Canonical IDs and
longer bot waits correct two application defects, but the exact real target
still returned native failure1200 after120.01s. Private URL lookup also failed
before a URL was produced. Native forward ancestry loss is supported by source
inspection; its causal role in this individual failure remains an inference.

## 3. Prevention mechanisms

| Priority | Mechanism | Action | Status |
| --- | --- | --- | --- |
| P0 | Actual protocol shapes | Dual file/file_id fields and equal basenames with differentIDs | Implemented |
| P0 | Temporal tests | Dedicated filedeadline, delayedresponse, longfailure crossingretryexpiry | Implemented |
| P0 | Safe diagnostics | Controlled action/reason/retcode without raw private payloads | Implemented |
| P0 | Honest acceptance | Keep native file failure unresolved despite passing synthetic tests | Recorded |
| P1 | Executable spec | Source-backed ID/deadline/retry/storage contracts | Updated setu-storage.md |
| P1 | Native capability | Require usable byte-transfer evidence before an alternate resolver claim | Ordinary-file path/stream passed; forwarded resource unresolved |

## 4. Expansion boundaries

Other media mostly provide URLs and keep their original identifier/deadline/
placement behavior. Do not broaden filesystem or HTTP permissions to disguise
a native resolver failure. Ordinary quoted-file saving was explicitly approved
and implemented as an alternate entry; its native path/byte transfer passed the
later isolated validation described below. Deployed command receipt remains
pending. An upstream
NapCat patch/version change is not inferred from the application implementation
authorization.

## 5. Knowledge captured

The project-owned `setu-storage.md` now records real raw field roles,
operation-specific wait bounds, safe error categories, atomic expired file
retry renewal, and tests that exercise these contracts. Research records source
anchors and sanitized live evidence. This is an application repository, not
the Trellis template source; no synthetic template directory was created.

## Follow-up: cache location, owner-only bytes and expired failures

The latest live ordinary-file get_file succeeded, but returned
`NapCat/temp/<basename>` rather than the mocked QQ nt_data layout (B/E).
The precise mounted path was therefore added for explicit file segments only.
Testing actual read access then found0600 source permissions: shared group
membership did not make the different-UID bot able to read it (E). Bounded
canonical-ID native streaming avoids changing permissions; real full-copy
validation and an independent original-cache hash comparison now pass.

Separately, retained source deduplication was incorrectly equated with
completion: expired failed rows were absent from the awaiting lookup (B/D/E).
An atomic source-state transition now accepts renewed source intent and
preserves successful checkpoints, while old prompt expiry stays effective.

Prevention: test actual native path shape and access before claiming capability,
carry a stream through metadata/chunks/exact completion with rejection/caps,
and test expired partial/zero-success source actions plus concurrent claims.
New specs capture source state separately from seen identity and scope the
native byte fallback. An API timeout fix alone could not establish these later
path/permission boundaries. No upstream forwarding repair is implied.
