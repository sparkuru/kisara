# Unified repository container lifecycle

## Goal

Remove deployment/preview lifecycle conflicts so users can stop, rebuild and
switch this repository's bots without manual Docker rm or ownership label edits.
The user explicitly requested a new task and a fix after reporting redundant
interlocking lifecycle guards.

## Confirmed evidence

- Work 7da12cd unified preview application image builds but retained separate
  ordinary/preview ownership. Records: 8feaa57 and task 10-12-telegram-tguid.
- deploy/preview-runtime.sh:362 rejects selected Compose containers lacking
  preview labels, even stopped ordinary instances. The actual ordinary
  kisara-telegram-1 is exited; fresh read-only checks establish the reported refusal.
- deploy/engines.sh:137 ordinary stop/down retain container objects; preview
  stop/down remove owned objects, preserving volumes.
- Preview rejects changed fingerprints, incomplete groups, existing groups on
  build and competing OneBot modes; its startup uses --no-recreate.
- COMPOSE_PROFILES/explicit targets, readiness, local API staging and streaming
  redaction are established contracts. No live service conversion has occurred.

## Requirements

- Use one repository-scoped ownership/selection boundary for ordinary and
  preview lifecycle operations; a preview label is not exclusive permission
  to manage this repository's selected Compose services.
- Same-repository ordinary/preview containers can be stopped/removed through
  either entry. Foreign project/repository containers stay protected, including
  collisions on Compose project and service names.
- Explicit startup/rebuild reconciles changed configuration/images and
  partial/stopped groups without manual label or fingerprint cleanup.
- Build prepares current selected application images without starting/stopping
  services merely to build. Startup applies desired Compose configuration/images.
- Only one OneBot mode can run against QQ state; an explicit selected mode can
  safely switch the repository-owned counterpart.
- Preserve volumes/login/state/cache/media, engine settings and group/public/
  native authorization. Preserve local Bot API readiness order and bounded errors.
- Status remains read-only with platform labels, credential redaction and
  readers-only Ctrl+C cleanup. No help/status-triggered repairs.
- Remove bespoke fingerprint/reuse/incomplete-group policy instead of adding
  force flags, another state machine or speculative compatibility framework.
- User decision: merge stop/down and retain only down, which stops and removes
  selected containers while preserving persistent storage. Remove the stop
  command/alias from the affected public lifecycle entrypoints.
- Explicit startup recreates selected application bots to reload startup-only
  TOML and environment; auxiliaries use normal Compose reconciliation.
- Failed preview startup reports bounded redacted diagnostics and leaves its selected
  containers inspectable. A following start retries/reconciles directly; down
  removes them. Remove attempt-label-driven automatic container rollback.

## Acceptance Criteria

- Stopped ordinary Telegram containers from this repo no longer produce the
  reported preview ownership refusal; foreign lookalikes fail before effects.
- Ordinary -> preview -> ordinary switching applies desired images/settings,
  retaining storage and unselected bots without operator label/removal steps.
- Startup recovers changed settings, rebuilt images and partial/stopped groups.
- Application startup reloads same-path TOML changes without unrelated engine
  configuration hashes; unchanged auxiliary IDs remain stable.
- Build can run with an existing repo group without lifecycle mutation.
- OneBot mode switching leaves only the requested active mode with retained data.
- Only down is advertised/accepted across the affected lifecycle entrypoints;
  stop no longer silently forwards. Down removes selected objects with data intact.
- Focused lifecycle/CLI/deployment tests, shell checks, independent isolation/
  data review and complete regression pass.
- Failed startup never emits ready, never deletes persistent storage or
  unselected containers, and retains created/recreated containers instead of
  automatically rolling them back. Diagnostics and direct retry remain available.

## Scope boundaries

Existing lifecycle helpers, focused tests, operations and project-owned specs.
No bot business/auth refactor, unrelated lock removal, dependencies, private
dotenv rewrite, broad cleanup, live account/service operation, commit/archive
or push is included in initial implementation scope.

## Planning status

Stop/down policy is resolved by the user's explicit response. Source and fixture
research is complete; design/implementation artifacts define the single lifecycle
and its failure behavior. The user approved the latest final summary with
“开始”; implementation and offline verification are authorized.
