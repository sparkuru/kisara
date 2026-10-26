# Execution and validation plan

1. Load this task's manifests/PRD/design, Python coding and backend/config specs.
   Record the preexisting dirty paths and preserve preview/startup-recovery work.
2. Add focused configuration and scheduler regressions using synthetic config,
   fake providers/senders/clocks and existing delivery journals. Establish the
   new timing/propagation cases fail before production changes when practical.
3. Wire the positive integer setting from TOML/env through Settings, Compose and
   adapters into both existing schedulers. Preserve longer rate-limit waits and
   all confirmed/permanent/uncertain delivery states.
4. Synchronize `.env.example`, both engine TOML examples, module docstrings and
   operations guidance. Main session owns task/mainline and spec updates.
5. Run focused news/settings/deployment/adapter tests with `./kisara.sh test`.
   Record exact results. Main dispatches independent Trellis check; reviewer
   runs required full offline regression once after final production changes.
6. Reconcile AC/results and project-owned contracts. Report new setting, default,
   sample usage and deployed-source rebuild requirement. No live restart,
   provider/account action, private env rewrite, commit/archive/push.
