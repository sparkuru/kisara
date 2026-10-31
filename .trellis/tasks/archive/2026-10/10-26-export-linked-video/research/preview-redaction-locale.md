# Preview redaction locale failure

## User report and boundary

The user reported `./kisara.sh preview build` succeeded, then `./kisara.sh
preview` failed with `sed: -e expression #2, char 25: Invalid range end` and
suppressed both gateway/application diagnostics. This blocks current video
export account recovery/native acceptance and is handled inside this active
task, preserving the separately implemented QQ terminal-QR work.

At investigation start, the workspace additionally contained the other task's
QQ login helpers, ANSI cleanup and log-view integration. Those are existing
authorized changes, not disposable work. Limit product edits to the shared
redaction boundary and focused regressions; do not revert QR rendering,
restart accounts, rewrite private configuration or claim prior full gates cover
this later workspace.

## Direct reproduction

GNU sed4.9 on this host has real C, C.utf8, POSIX, en_US.utf8 and zh_CN.utf8
locales installed. No private env file, Docker daemon or provider was involved:

```bash
LC_ALL=en_US.utf8 bash -c 'source deploy/preview-runtime.sh; preview_secrets=(); preview_filters=(); preview_redact_values show; printf "safe fixture\n" | sed -E "${preview_filters[@]}"'
```

Result: exit1, the exact user-reported expression2/char25 error. The same
command under zh_CN.utf8 failed with the equivalent localized error. C and
C.UTF-8 passed and retained the input.

The second expression is the added ANSI CSI removal rule containing ASCII
ranges `[0-?]`, `[ -/]` and `[@-~]`. POSIX range interpretation depends on
LC_COLLATE; this is an actual compile failure under non-C collations, not a
missing image/package or evidence of an invalid Bilibili session. Bash's
matching CSI expression has the same locale dependency. The QR snapshot path
also invokes the shared sed array directly and must stay consistent with
diagnostics, stream preflight and stream filtering.

## Required repair and verification

- Make only internal terminal-control/redaction interpretation deterministic;
  preserve caller locale, Unicode text and the existing whole-symbol QR filter.
- Cover buffered diagnostics, live streaming, QQ snapshot and Bash ANSI
  normalization without disclosing secrets or falling back to raw output.
- Preserve the terminal-QR feature, non-TTY behavior, ownership/read-only
  viewing, bounded readers and existing exported session redaction.
- Add a regression that fails on the original source. Container test locales
  may not include en_US/zh_CN, so record actual locale availability and do not
  treat an unsupported-locale fallback to C as reproduction. Main will repeat
  the real installed-host locale matrix independently.
- Run focused pipeline/CLI tests, independent checking and required project
  verification. Record code/test changes and actual live readiness separately.

## Related baseline

The separate QQ-QR task records a later full suite with1289 passes,1 skip and
one video cleanup timing failure (that test passed alone). Preserve that
limitation until an actual new gate establishes current results; do not
silently relabel the old run as green or re-run failed tests to hide flakiness.

## Bug analysis

### 1. Root cause category

Implicit assumption and coverage gap: CSI grammar is an ASCII byte contract,
but POSIX/Bash regex ranges were evaluated in the caller's collation. Existing
C/POSIX/C.UTF-8 fixtures did not exercise a genuine non-C collation.

### 2. Why earlier checks missed it

Passing byte-oriented locales established Unicode preservation, not whether
the new ASCII ranges compile in en_US/zh_CN. Merely setting an unavailable
locale in a slim image silently falls back and cannot close that gap. A sed-only
repair is also incomplete: Bash normalization must happen before literal
replacement or later stripping can reconstruct an undisclosed credential.
Independent review reproduced that same ordering defect with CR inside a
synthetic credential. The repair therefore also normalizes remaining ASCII
controls before replacement; CR/backspace/tab/DEL regressions cover the case.

### 3. Prevention mechanisms

- Scoped `LC_ALL=C` at internal regex boundaries; caller locale remains intact.
- Shared foreground filter helper for buffered diagnostics/preflight/snapshot;
  direct byte-locale background sed preserves actual PID ownership.
- New boundary, synthetic ANSI/OSC/control secret, Unicode, failure and PID regressions.
- Real installed host locale probes supplement explicitly reported slim-image
  locale skips; no new package/toolchain is required in production.

### 4. Systematic expansion

Checked diagnostics, streaming preflight/live filtering, QQ snapshots and Bash
preprocessing as one contract. An initial background-helper implementation
changed the tracked PID; a new regression caught it, and direct background sed
restored the existing lifecycle ownership. Existing QR behavior remains intact.

### 5. Knowledge capture

Updated shared logging and validation specs with executable locale/ordering/PID
contracts and actual-locale test requirements. This bot repository has no
`src/templates/markdown/spec` template tree to synchronize. No commit is
authorized by the current task; specification changes remain reviewable.

## Independent main-session verification

A standard-library-only host driver invoked the new fixture helper against
production shell functions, without pytest or application Python imports.
All19 probes passed: C/POSIX/C.UTF-8/en_US.utf8/zh_CN.utf8/unset-LC_ALL across
buffered, streaming and QQ snapshot paths, plus a failed-filter closure probe.
Both non-C locales are really installed. Chinese output and expected redaction
matched exactly; internal sed saw C, caller LC_ALL stayed unchanged and hidden
ANSI/OSC synthetic secrets never appeared in output.

A real read-only `LC_ALL=en_US.utf8 ./kisara.sh preview status onebot` invocation
followed actual logs, showed no range/redaction failure, and exited130 after
SIGINT. Output was captured privately and discarded; only booleans were emitted.
Container IDs/start times for OneBot, NapCat and Telegram remained unchanged.
The ready summary was correctly absent while QQ still awaited login. This
smoke was before the direct-background-PID adjustment; repeat final-source
checks were subsequently repeated after independent review, without recreating services.

Final-source host verification again passed19 probes with the expanded
ANSI/OSC/CR/backspace/tab/DEL payload. Every streaming case also asserted that
the tracked sanitizer PID equals the actual sed PID. The real en_US status
smoke again followed logs with no range/redaction error and exited130 on SIGINT;
its entire viewer process group was gone afterward. Container IDs/start times
were unchanged, and no ready summary was fabricated while QQ awaited login.

## Final normalization compatibility correction

Review then demonstrated that removing tabs before generic redaction collapses
`Bearer<TAB>unconfigured-token` and loses its required separator. The first new
full run was intentionally stopped after806 passes/7 skips/2 existing warnings
in636.65s; it is incomplete intermediate evidence, not a final pass.

The least-change correction canonicalizes only a strict complete Bearer
prefix/separator while preserving token bytes. Remaining controls are then
removed, configured literals replaced and the existing generic sed grammar
applied. Pre-redacting a partial token before controls are normalized would
leave suffixes of a configured split credential. The rest-scanning loop avoids
rescanning inserted text; optional separators are not introduced.

The shared fixture now contains19 Bearer cases: known/unknown tokens with tab,
CR, VT and FF; split configured tokens; multiple/lowercase/already-redacted/
empty/ordinary-word input; and quote/apostrophe/comma/semicolon boundaries.
After the correction, final container focus passed43/6 unavailable-locale
skips in108.92s. Main's full host matrix passed19 probes again with all19
Bearer cases in each production-boundary payload, including real en_US/zh_CN,
exact output, direct sanitizer PID and caller-locale preservation.

The final full gate starts only after this bounded adversarial review completes.
