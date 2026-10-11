# Research: NapCat preview readiness after authorized OneBot conversion

- Query: Why can canonical OneBot preview time out on NapCat after its OneBot socket starts and Kisara connects, and what is the smallest evidence-backed correction?
- Scope: internal; source and synthetic probe investigation only. Root owns actual containers, private configuration and logs.
- Date: 2026-10-11

## Findings

### Files found

| File | Responsibility |
| --- | --- |
| `deploy/preview-runtime.sh` | Running-state and service probes, bounded wait, owned rollback, listener/mapping summary. |
| `deploy/napcat-entrypoint.sh` | Initial config bootstrap and authoritative OneBot token/socket configuration. |
| `deploy/compose.yaml` | Fixed container UI6099 and OneBot3001; configurable host UI publishing; persisted login/config mounts. |
| `deploy/preview-console.sh` | Public preview help and semantic/redacted diagnostic presentation. |
| `deploy/preview-listeners.js` | Node-based Linux TCP listener enumeration. |
| `tests/unit/test_preview_lifecycle.py` | Recording fake Docker fixture with ownership/lifecycle/readiness flags. |
| `tests/unit/test_preview_readiness.py` | Real Python marker/PID lifecycle and listener-decoding checks. |
| `src/kisara/bot/adapters/onebot_v11.py` | Marks the current OneBot process ready after authenticated WebSocket connection; clears on disconnect. |
| `docs/operations.md` | Existing intended NapCat browser route `/webui`. |
| `.trellis/tasks/10-10-telegram-tgsetu/research/unified-entrypoint.md` | Latest script-retirement approval and separately authorized OneBot conversion. |

### Current probe and the route mismatch

`preview_ready_one` first checks container Running (`preview-runtime.sh:368–370`).
NapCat then executes a Node program that requires **both** HTTP `fetch("http://127.0.0.1:6099")` with `Response.ok` and a successful TCP connection to IPv4 loopback3001 (`:378–380`). Failure is deliberately conservative; a running container or open WebSocket alone does not satisfy the whole group.

However, existing operations guidance tells users to open `http://127.0.0.1:6099/webui` (`docs/operations.md:261–265`). The probe requests `/`, and the summary also emits root-only browser URLs (`preview-runtime.sh:567–575`). A NapCat runtime with `/`404 and `/webui`2xx therefore meets the intended UI availability contract while being rejected by the existing probe.

Synthetic reproduction ran the exact production JavaScript under available host `/usr/bin/node`, substituting only deterministic fetch/TCP fixtures (no actual sockets, Docker or credentials). Root404 + WebUI200 produced exit1; root200 produced exit0. This establishes the mechanism, **not** the actual private runtime response.

Smallest route correction, **if actual HTTP facts confirm that case**:

1. Probe the documented `/webui` route, keeping the 2xx requirement, bounded timeout and OneBot TCP conjunct.
2. Emit the same `/webui` path in all NapCat browser summary variants (loopback, wildcard host candidates, IPv6 and explicit address).
3. Keep the separate Kisara process/PID/engine readiness marker, listener checks, owned-attempt rollback and state-preserving lifecycle unchanged. Do not accept any HTTP error merely because the socket exists.

### Config and runtime assumptions

- Compose `NAPCAT_WEBUI_PORT` configures the **host** port, mapping to fixed container6099 (`compose.yaml:17–18`); changing that input alone is not a reason to probe a different container port.
- `NAPCAT_WEBUI_BIND` configures host publishing, not NapCat's internal UI listener. Compose mounts persisted `data/napcat/config` and `data/napcat/QQ` (`:19–22`).
- The entrypoint bootstraps configuration only when `napcat.json` is absent (`napcat-entrypoint.sh:25–34`), then rewrites only `onebot11.json` with wildcard host3001 and the shared OneBot token (`:41–69`). It does not synchronize or reset persisted WebUI enabled/host/port settings.
- Therefore a disabled UI, changed persisted internal UI port, IPv6-only/specific-address UI bind, missing global Node fetch, or actual UI non-success response can independently fail the probe while OneBot remains connected. Do not infer which condition occurred from WebSocket logs alone.
- OneBot's current marker is published at the authenticated connection seam (`onebot_v11.py:145–146`) and invalidated on disconnection (`:160`). This supports transport lifecycle readiness, not actual QQ feature delivery.
- Wait's generic failure and login-preparation hint (`preview-runtime.sh:407–411`) do not identify which NapCat conjunct failed. Raw probe errors are redirected to a temporary probe log (`:380`) and are not separately printed by diagnostics, which only include bounded service logs (`:419–432`). Increasing timeout cannot repair a persistent route/capability mismatch.

### Evidence root should obtain

Use root-owned sanitized runtime inspection if available; do not print config files, tokens, account IDs or bodies:

- Node version and `typeof fetch`.
- Actual container6099 listening address/family.
- Status code only for HTTP `/` and `/webui` over the same address used by the probe.
- TCP3001 connect result.
- UI enabled/internal port/address facts only if the above require config diagnosis.

If Node fetch is unavailable, that is a different capability failure and should be diagnosed explicitly before introducing a fallback. If UI is deliberately disabled or internally moved, source's advertised fixed UI contract and persisted settings need an explicit compatible decision; do not silently alter user data or weaken readiness.

### Test boundary and smallest useful regression

Fake Docker's exec branch (`test_preview_lifecycle.py:98–111`) returns the stored `ready` flag and never executes production JavaScript. Consequently existing lifecycle green gates cannot catch the route mismatch or Node capability absence. Existing actual Python readiness tests do not cover the NapCat JavaScript (`test_preview_readiness.py:38–61`).

Required regression for a route fix:

- A deterministic HTTP fixture where `/` returns404 and `/webui`200, while OneBot TCP is reachable, should be accepted by the actual probe; unavailable UI or TCP must still fail. Execute actual Node program when runtime capability permits, or at minimum make fake Docker's NapCat exec enforce the requested route against that behavioral fixture; report the latter's execution limit.
- Browser summary assertions should require `/webui` for advertised NapCat URLs across host binding variants.
- Keep existing absent/foreign/changed ownership, stopped-data preservation, rollback, status no-start and Telegram isolation assertions.
- A sanitized real NapCat probe/status smoke complements the synthetic regression. Do not claim feature acceptance from that smoke.

### Related specs and references

- `.trellis/spec/trellis-plus/validation.md:194–220`: real bounded service probes, live process marker, actual paths/listeners and no false ready summary.
- `.trellis/spec/trellis-plus/cli-entrypoints.md:38–46,69`: unchanged owned preview identity and explicitly authorized conversion boundary.
- `.trellis/spec/trellis-plus/configuration-storage.md:243,375`: persisted QQ/config and loopback default publishing.
- Internal primary source: `docs/operations.md:261–265` documents `/webui`. No external documentation was used; installed NapCat/Node version and actual route remain root-owned runtime facts.

## Caveats / Not Found

- No actual container operations, private config reads, account access, source/test edits or Git operations were performed by this researcher.
- At research time the first authorized attempt had already rolled back its own containers; only root's sanitized description (WS server3001 and client connection) was available.
- The route mismatch is demonstrated by source and synthetic reproduction. Actual failure cause remains conditional until runtime HTTP/capability facts arrive.
- Fix guidance is bounded to the probe/summary and meaningful tests. Preserve fixed deployment ports and user login/config data; do not convert a UI failure into unconditional transport readiness.

## Confirmed runtime evidence and final bounded recommendation

Root subsequently supplied sanitized observations from the second bounded attempt:

- `docker exec kisara-napcat-1 node ...` failed before the script ran: OCI reports no `node` executable in container PATH. `nodejs` is absent too.
- Available commands include `python3`, `curl`, `bash`, and `awk`.
- Safe persisted WebUI fields are `disableWebUI=false`, port6099 and bind `::`.
- Using container Python stdlib, IPv4 loopback HTTP `/` **and** `/webui` each returned200; TCP IPv4 loopback3001 was reachable.
- An IPv6 urllib probe reached502, with inherited proxy settings a plausible cause; local probes must explicitly disable proxies instead of relying on ambient proxy/no_proxy values.

These facts establish **missing Node as the immediate root cause**. The earlier documented route mismatch is a source inconsistency, but root404 was not present in this runtime and is not the cause of this failure. Login and timeout increases do not repair executable absence.

The smallest coherent fix now supported by observed capabilities is to reuse the existing `deploy/preview-probe.py` Python stdlib implementation for NapCat only:

1. Add a NapCat HTTP-plus-TCP predicate using fixed container loopback6099 and3001, explicit bounded timeouts, `urllib.request.build_opener(ProxyHandler({}))`, a successful HTTP status and no response-body logging. The documented `/webui` route is suitable and actually returned200.
2. Execute the existing source through container `python3 -c "$(cat .../preview-probe.py)" napcat`, so NapCat needs no new image package or file mount. Host shell quoting preserves source as one literal argument. Confirm installed Python version supports the script's annotations, or defer annotation evaluation to preserve compatibility.
3. Execute the same source with argument `listeners` for NapCat summary. Its existing listener decoder already has real IPv4/IPv6/DNS-exclusion tests (`preview-probe.py:25–45`; `test_preview_readiness.py:183–198`), avoiding a second shell/JS decoder.
4. Keep Music's established Node probe/decoder path unchanged. Preserve current application marker checks for Kisara/Telegram/Official and all ownership/rollback constraints.
5. Require the canonical lifecycle fixture's NapCat exec branch to reject Node/NodeJS requests (model the observed capability) and accept the Python path; retain separate generic unready flags. Run actual stdlib helper behavioral tests for HTTP success/failure, TCP failure, proxy bypass, and response-body privacy, then existing listener/PID tests and full canonical regression.
6. Root should run one sanitized real NapCat readiness/listener smoke and bounded canonical preview start/status. Record operational outcome separately from mocked full-suite results; do not claim feature messaging from ready status.

This recommendation supersedes the route-only conditional fix as the primary correction. Neither source-built image changes, new dependencies, login reset nor private config edits are required by the evidence.

### Final direct HTTP evidence

Root subsequently confirmed Python3.10.12 and direct HTTPConnection statuses:
`/`301, `/webui`301, `/webui/`200, `/webui/index.html`200. The earlier urllib200
facts are final statuses after automatic redirects, not direct root responses.
With a direct proxy-free HTTPConnection implementation, probe `/webui/` so
strict2xx and no redirect/proxy behavior remain. A local fixture returning301
at root and200 at `/webui/` must validate the actual helper. Browser root summary
URLs still work via the server's local redirect; changing all summary paths
is unnecessary for this correction. Missing Node and root redirects are both
covered by the final stdlib probe and canonical lifecycle tests.
