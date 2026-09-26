# Database Guidelines

## Scope and signatures

Durable feature state uses standard-library `sqlite3`; there is no ORM or
shared migration framework. Stateless requests use no database; dispatcher
message deduplication is bounded process memory and does not survive restart.

Sources: `src/kisara/infrastructure/persistence/news_delivery.py` and
`src/kisara/infrastructure/persistence/setu.py`.

- `NewsDeliveryStore(state_dir: str)` exposes `was_sent(day, group_id) -> bool`
  and `mark_sent(day, group_id) -> None` for groups, plus
  `was_private_sent(day, user_id) -> bool` and
  `mark_private_sent(day, user_id) -> None` for personal QQ recipients.
- `SetuStore(state_dir: str)` owns batch claims, prompt identity, per-item
  checkpoints, expiry, and restart recovery.

## Storage and schema contracts

State lives under `Settings.state_dir` / `KISARA_STATE_DIR`, default
`data/kisara`. Compose supplies `/app/state` through the `kisara_state` volume;
this is separate from confirmed setu media. See
[configuration/storage](../trellis-plus/configuration-storage.md) for mappings.

| Database | Current schema and keys |
| --- | --- |
| `news_delivery.sqlite3` | Unchanged `deliveries(day TEXT, group_id TEXT)` for groups; additive `private_deliveries(day TEXT, user_id TEXT)` for individuals; all columns NOT NULL, each table keyed by its day and recipient ID |
| `setu.sqlite3` | `batches` keyed by `id`, index `batches_status(state, deadline)`; `seen` primary key `(instance_id, message_id)` |

Setu stores media metadata in `media_json`; binary media stays in the file
archive. The setu database has mode `0600`. News completion is recorded only
following successful sending; either mark method prunes both news tables for
records older than 30 days relative to the supplied day. Setu retains seen IDs
and old terminal metadata for seven days: new batches prune seen IDs, and
`expire()` prunes terminal
metadata. These operations do not delete archived files.

## Transactions and query patterns

Use parameterized values and short-lived connection context managers. A
connection context commits or rolls back; it does not itself promise explicit
connection closure. Setu's `_connect()` uses `timeout=10` and `sqlite3.Row`.
`add_setu()` uses `BEGIN IMMEDIATE` to claim the source and create a batch
atomically. Conditional updates plus `rowcount` claim prompt/save transitions.

Example from `NewsDeliveryStore.was_sent`:

```python
with sqlite3.connect(str(self._path)) as database:
    row = database.execute(
        "SELECT 1 FROM deliveries WHERE day = ? AND group_id = ?",
        (day, group_id),
    ).fetchone()
return row is not None
```

## Recovery and error matrix

| Condition | Existing behavior |
| --- | --- |
| State directory missing | Store initialization creates it |
| Repeated source `(instance_id, message_id)` | `add_setu` returns `None`; no second batch |
| Save already claimed or confirmation expired | `claim_save` returns `False`; no new save claim |
| Setu `PRAGMA user_version < 2` | Expire legacy collecting batches; set version to 2 |
| Restart with batches in `saving` | Return them to `awaiting` so unfinished files can be retried |
| Initialization filesystem/SQLite error | `bot/main.py` logs failure and returns exit code 2 |

Do not assume deployed databases will be recreated. A schema change needs an
explicit upgrade/recovery design and tests against earlier state; existing
`user_version` handling is feature-local.

## Cases and tests

Good: reopen `NewsDeliveryStore` and retain the sent group/day pair. Base:
`/roll` has no persistent state. Bad: record send completion before receipt,
interpolate message values into SQL, or put state at an unmounted container path.

`tests/unit/test_news_delivery.py` asserts reopened state and isolation by day
and recipient kind/ID, reopening a deployed group-only schema without losing
group records, and both-table pruning. See the complete
[scheduled news contract](../trellis-plus/configuration-storage.md#scheduled-news-to-groups-and-private-qq-recipients)
for configuration and protocol assertion points. `tests/unit/test_setu.py`
covers duplicate sources, confirmation identity, saved-item preservation,
partial retry, authorization, and expiry.
For changes, also test the affected legacy/restart path rather than relying on
a fresh database alone.

Wrong: unconditionally start saving for every repeated confirmation.
Correct: require `claim_save(batch_id, now)` to succeed, checkpoint each finished
item with `update_media`, and keep only unfinished work retryable.
