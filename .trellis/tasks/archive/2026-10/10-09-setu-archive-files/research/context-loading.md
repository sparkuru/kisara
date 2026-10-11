# Context loading checkpoint

The 2026-10-09 approved Trellis Plus loading repair preserved every existing
context entry and task state. Shared policy is prioritized. Installed injection
limits remain unchanged: 32768 bytes/file, 131072 total including block headers.
The full setu manifests exceed that total before task artifacts. Registration is
verified statically; an actual new setu-agent dispatch was not performed.

On the next setu dispatch, read full files when their native blocks are truncated
or index-only, even if a hook marker exists. Before implementation/check, confirm
the full prd.md, design.md and implement.md from this task directory are read.
Static budget review predicts index-only implementation research:

- napcat-forward-file-native-limit.md
- live-file-probes.md
- live-cache-and-expired-retry.md

For checking, the predicted index-only research is
napcat-forward-file-native-limit.md and live-cache-and-expired-retry.md.
These files are in this research directory. Added headers or later entries can
shift the boundary; inspect resolved input and read any other relevant incomplete
file explicitly. Do not delete research or raise protected loader limits to hide
this limitation. No native-input completeness or live acceptance is claimed here.
