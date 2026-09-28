# Quote triggering message in setu results

## Goal

Make each setu archive result visibly reply to the user message that triggered that save.

## Requirements

- Keep the current quoted-forward request, confirmation prompt, and quoted confirmation workflow.
- When a user quotes the bot's confirmation prompt and replies with a confirmation word, quote that user's confirmation message in the final archive result.
- When a user quotes a forward and sends a direct-save word, quote that user's direct-save command in the final archive result.
- Apply the same rule to partial-failure results and retry results. Preserve the existing result text, save state, and retry target behavior.
- Keep the change confined to the private OneBot setu workflow; do not alter unrelated replies.
- Require `max_file_bytes` and `max_batch_bytes` as quoted whole-number `K`, `M`, or `G` values using 1024-based units. Reject the old TOML integer form, malformed values, zero, and negative limits at startup.
- Express the existing 100 MiB file limit and 1 GiB batch limit as `"100M"` and `"1G"` in the private and example setu config without changing effective limits.

## Acceptance Criteria

- [x] The normal confirmation result carries a reply segment targeting the confirming user's message ID.
- [x] The direct-save result carries a reply segment targeting the direct command's message ID.
- [x] A retry result targets the retry command's message ID, while partial-failure retry selection still uses the prior bot result ID.
- [x] Existing prompt quoting, authorization, save behavior, and result text remain correct.
- [x] String limits convert to byte integers before service use; old integer values and invalid strings fail validation, and the batch limit still covers the file limit.
