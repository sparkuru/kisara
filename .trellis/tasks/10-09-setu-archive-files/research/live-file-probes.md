# Sanitized live file resolver evidence

Inspected 2026-10-09 after the user reported a failed private merged-forward
archive direct save. All API calls targeted that existing failed source. No
messages were sent, no containers were restarted, and no private configuration
was changed. One get_file probe requested native download into NapCat's own
cache; it did not complete or return any source path. Archive contents were
never opened/extracted and no successful archive file was published.

## Runtime and source shape

The user externally recreated OneBot and NapCat at approximately 04:32:44 UTC.
Read-only source inspection inside OneBot confirms the archive naming code was
loaded, but canonical file-ID precedence was not yet fixed. The runtime was not
still using the original pre-feature image.

The original failed batch contains one file-kind `.7z`, reported size
109092709 bytes, no URL, and only an exception-class checkpoint. Its stored
resolver string equals its basename. Fresh lookup of that exact quoted forward
returned separate `file` basename and `file_id` opaque key; those fields are
distinct. Neither a separate name nor URL was supplied.

The enclosing converted node has `message_type=private`, no group ID, and
exactly one `file` segment. Therefore a group-origin HTTPS fallback does not
apply, and a text-before-file first-element bug is not established for this
node. Native message/MD5 prerequisites remain unobservable through the normal
OneBot API response.

## Executed probes

| Probe | Result |
| --- | --- |
| Read-only SQLite structural query | One failed/expired file, no saved path; private values excluded |
| get_msg/get_forward_msg for exact failed source | Distinct canonical ID and original basename; private inner file node |
| get_file with freshly converted canonical file_id, 180-second diagnostic deadline | Failed, retcode 1200, elapsed 120.01 seconds; no returned path or URL |
| get_private_file_url with same canonical ID | Immediate failure, retcode 1200; fixed error classified as missing real fileUUID prerequisite |
| Exact basename metadata search within existing allowed QQ File cache subtree | One allowed File directory, no exact-basename candidates; no contents inspected |

No raw request identifiers, basenames, signed URLs, response bodies, account IDs,
or credential values were printed or retained in research artifacts. Credentials
were read only inside the target bot process environment for its existing
NapCat connection and were never placed in tool arguments/output.

## Conclusions

Canonical identifier selection and a file-specific response deadline fix real
Kisara contract defects. They do not fix this native NapCat 120-second download
failure. Private URL lookup fails before a URL is generated. Existing HTTPS and
local-cache checks must remain intact; neither an HTTP permission change nor
an arbitrary NapCat temporary mount is supported by these observations.

Installed source indicates forwarded-file ancestry is lost in the file cache,
but its causal role in this specific native timeout is an inference. The live
failure remains unresolved. No version update, dependency patch, or alternate
save entry point is assumed to work without evidence/authorization.

## Upstream corroboration and its limits

The upstream [NapCat issue #900](https://github.com/NapNeko/NapCatQQ/issues/900)
reports the same private-file URL prerequisite error on an older version and
is closed as not planned. It corroborates that this error is an upstream
reported symptom, not proof of the same underlying cause or a current fix.

## Product scope decision

The user explicitly approved adding quoted ordinary-file messages as an
alternative entry after the scoped question. This is now in scope, using the
same naming/confirmation logic. Ordinary-message native transfer still requires
verification; approval does not prove that the native download will work or
authorize an upstream dependency patch/source-policy relaxation.
