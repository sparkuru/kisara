# Prepared account acceptance (not executed)

Implementation approval covers offline checks. These steps require a separately
authorized Telegram account/environment operation. Do not operate the existing
token owner or change its endpoint as a side effect of tests.

## Setup and migration

Follow [operations](../../../docs/operations.md#telegram-media-archive-and-local-bot-api)
for the dedicated TOML, global/feature user IDs, server-only API ID/hash,
local-mode endpoint and explicit cloud logOut. Stop the previous token owner
before a switch. Retain SQLite/cache/archive volumes. Use targeted Telegram
lifecycle; preserve OneBot and official processes.

Before sending media, verify server readiness and identical cache path
`/var/lib/telegram-bot-api`, server writable / bot read-only, both UID 10001.
Confirm no published server host port and writable configured archive root.
Do not print tokens, API hash, raw rendered Compose configuration or SDK URLs.

## Acceptance cases

1. With archiving off, send a captioned photo and document: no archive jobs/files.
   Confirm `/setu` is unavailable and enabled `/tgsetu` appears in help. A denied
   private user/group must produce no archive effects.
2. Enable `/tgsetu on`. Forward a video with the PRD caption example: preserve
   dots/brackets/Unicode and ordered `-@tag` suffixes, with the media extension.
   Send `pack.tar.gz` with `资源合集 #tag1 #tag2`: expect
   `pack-资源合集-@tag1-@tag2.tar.gz`.
3. Forward a mixed-media album and multiple independent messages. Verify one
   file per real item, shared initial album caption, ordinals before tags and
   separate captions for independent messages. Results count actual received
   Telegram messages/files and logical units, not the original multi-selection.
   Late members must be accepted without renaming already published files.
   Repeat a late-caption album while all download workers are occupied: its
   initial naming window must still close at the configured deadline.
4. Use a known fixture larger than 20 MB within configured caps. Verify cache
   readability, final byte count and independent SHA-256. Observe bounded copy
   memory; photos uploaded as photos may be compressed by Telegram, so use a
   document for an original-byte assertion. No partial final file may appear.
5. In an isolated acceptance instance, create a controlled failing member
   without deleting server sessions or changing live production credentials.
   Keep successful siblings; `/tgsetu retry <source-message-id>` processes only
   eligible failed files. Remove the fixture failure, retry and verify frozen
   names. Repeat conflicting-name media: preserve prior bytes.
6. Turn off while accepted work remains: accepted jobs finish and new media is
   ignored. Restart the isolated instance: activation remains off, successful
   checkpoints/files stay intact, unfinished owned work resumes/reconciles.
   Repeat while on to verify persisted activation.

## Evidence and rollback

Record versions, targeted commands, safe source IDs, filenames/counts/hashes,
restart/partial-result behavior and any remaining failures in validation.md.
Keep account identifiers and credentials out of tracked records.

Endpoint changes require recreation; feature TOML changes require restart.
Rollback preserves all volumes and requires a controlled owner stop/logout and
Telegram's cloud re-login timing. Do not reset project volumes or remove active
downloads/session databases. Notifications are an in-memory queue; a notice
lost on shutdown does not erase durable archive truth. Inspect the configured
archive; eligible failures can be retried using their source message ID.
