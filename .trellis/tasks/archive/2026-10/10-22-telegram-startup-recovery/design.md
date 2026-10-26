# Telegram startup recovery design

## Boundary and failure model

Keep recovery in the existing Telegram adapter, which owns SDK objects, request
clients and poller shutdown. Main keeps lazy optional-engine imports and safe
process exit reporting. Do not introduce a second lifecycle supervisor or use
SDK private retry/state helpers.

The supplied logs do not identify their original error. Reproduce startup
transport failures using the pinned public SDK request interface, then fix the
verified lack of recovery and missing safe classification. Preserve this
distinction in the validation report.

## Attempts and ownership

Allow three total startup attempts. Only transient transport/network failures
qualify; exclude BadRequest despite its NetworkError inheritance, along with
InvalidToken, Conflict, Forbidden and unrelated exceptions. RetryAfter and
other non-network API failures retain explicit failure behavior.

Initialization and polling bootstrap belong to the startup boundary. SDK app
start/programming failures and later worker failures are not restart triggers.
Clean up the failed attempt's request clients, application and poller before
creating a replacement through public SDK methods. The existing partial-init
cleanup closes requests, so recreating attempt-owned objects avoids reusing
closed clients or stale SDK initialization flags. Preserve the original safe
failure classification if cleanup also fails; do not retry on uncertain cleanup.

Wait 1 then 2 seconds between failed attempts using the existing stop/cancel
mechanism. A stop requested while waiting prevents the next attempt. Keep
drop_pending_updates=False. The successful attempt enters the existing worker,
scheduler and receive/send lifecycle exactly once.

## Diagnostics and readiness

Report controlled startup phase names and safe exception categories at the
handling boundary; never format the exception value or chained SDK traceback.
Keep SDK/httpx/httpcore suppression. Main's generic process failure must include
useful safe classification or be accompanied by the adapter's classified
failure without duplicating raw information.

Failed attempts must not emit polling ready or publish ready state. Keep the
current successful-poll/application-running readiness contract, clear readiness
on failure and shutdown, and retain existing fatal credential/ownership handling.

## Compatibility and rollback

No CLI/env/endpoint/storage change or SDK upgrade. Normal successful startup
remains one attempt. Only failed transient startup gains a bounded delay; fatal
errors remain explicit. Revert this task's adapter/diagnostic/test changes to
roll back, preserving prior preview streaming work and stored state.
