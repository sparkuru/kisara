# Readiness-independent streaming implementation evidence

## Actual cause and previous blind spot

The user's `Recent bounded diagnostics` output identifies a readiness-gated
failure/cleanup path. The earlier locale fix was real but exercised only an
already-ready status. It could not establish that bare startup or unready status
ever entered the follower. The reopened reproduction and approved contract
revision are recorded in `readiness-diagnosis.md`, `prd.md`, and `design.md`.

## Implementation

- `deploy/preview-runtime.sh`: separate reader setup, nonblocking status reaping,
  and attached waiting. Setup executes in the parent shell, retaining every PID
  for its existing cleanup traps. Startup starts sanitized readers after selected
  containers are collected, before the existing bounded readiness wait; genuine
  readiness still controls the summary, then the command remains attached.
- Unready status emits a warning and follows existing owned bot logs without a
  ready banner or service mutation. Missing/foreign selections still fail;
  auxiliary-only status stays finite. Actual reader EOF remains finite.
- Readiness checks detect reader/sanitizer failure between probe passes and
  before reporting success. Stream failures remain nonzero. Startup now requires
  `mkfifo`. INT/TERM record cancellation separately, skip duplicate diagnostic
  dumps only after viewing started, reap readers, and retain 130/143. Genuine
  startup failures/timeouts still produce bounded diagnostics for all selected
  services, including auxiliaries.
- `deploy/preview-console.sh`: describe attached startup, readiness-independent
  status, redaction, and data-preserving viewing cancellation.
- `tests/unit/test_preview_lifecycle.py`: explicit fake probe readiness files
  independently control running application readiness. Persistent fake streams
  prove prompt mixed-platform output while unready, delayed safe lines, a real
  readiness transition, continued attachment, parent-only INT/TERM before/after
  readiness, no duplicate diagnostics or service mutation, and prompt startup
  reader/sanitizer failure. A genuine timeout still includes music diagnostics.
  Existing finite-fixture expectations now distinguish warning/no-ready EOF0
  from missing/foreign failure rather than asserting all unready status exits1.

No live dotenv/account/API/start/rebuild operation, SDK readiness change,
automatic reader reconnect, or service repair is part of this implementation.

## Before/after validation

`./kisara.sh test tests/unit/test_preview_lifecycle.py -k 'start_streams_during_readiness or unready_status_follows or start_stream_failure_surfaces or start_timeout_retains_auxiliary' -q`

- Before production changes: **8 failed, 182 deselected**, 76.75 seconds.
  Startup never emits the history sentinel, unready status exits1, stream failure
  remains hidden behind readiness, and no live view precedes the timeout.
- After implementation: **8 passed, 182 deselected**, 26.41 seconds.

The independent checker subsequently strengthened the existing four startup
cases with localized streams and, for ready transitions, an additional delayed
safe UTF-8 line from each selected service after the ready summary. Its
supplemental command
`./kisara.sh test tests/unit/test_preview_lifecycle.py -k start_streams_during_readiness -q`
passed **4 tests, 186 deselected**, in 13.55 seconds. The combined gate below
collected the preceding definition before this test-only assertion extension;
production source was unchanged. See `streaming-review.md` for independent
review and the required full regression.

The original branch-characterization probe also passed all three scenarios in
the existing Docker development wrapper before the contract revision.

`bash -n deploy/preview-runtime.sh deploy/preview-console.sh` passed. ShellCheck
and shfmt are unavailable; neither was installed. Application lint/type checks
are not configured. Wrapper checks run in Python3.12 against isolated recording
Docker fixtures; they do not prove live account behavior or every declared
Python version.

`./kisara.sh test tests/unit/test_kisara_cli.py tests/unit/test_engine_deployment.py tests/unit/test_preview_lifecycle.py tests/unit/test_preview_readiness.py -q`
passed **289 tests, 1 existing skip**, in 547.54 seconds. The skip remains the
development image's unavailable Git executable. There were no failures or new
warnings. No production correction was required after the initial eight-test
success. The checker owns the full-suite result and independent review.

Final `bash -n kisara.sh deploy/engines.sh deploy/preview-runtime.sh deploy/preview-console.sh`,
`./kisara.sh preview --help`, and `git diff --check` passed. Help performs no
configuration or Docker operations. The test assertion strengthening described
above was the only change while the combined gate ran; its supplemental four
cases cover the final definition.

Implementation evidence ownership is now handed back to the main session.
No commit/archive or live account validation was performed by the implementer.
