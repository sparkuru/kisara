# Retained Third-Party Material

This inventory links existing component-scoped original notices. It does not
replace them, a root license, or source-specific obligations. When retained
content/version changes, verify the exact source notice, keep original text and
inline declarations, and reconcile this inventory. Directory location never
assigns a third-party template/code the application's license.

| Material/version | Verified source | Retained paths | Exact notice/provenance |
| --- | --- | --- | --- |
| Trellis 0.6.17, AGPL-3.0-only | Installed @mindfoldhq/trellis 0.6.17 distribution; scoped LICENSE bytes match | Protected .trellis templates/scripts/agents/config and managed platform material | [.trellis/LICENSE](../.trellis/LICENSE), [.trellis/THIRD_PARTY.md](../.trellis/THIRD_PARTY.md); matching package has no separate NOTICE/COPYRIGHT |
| Kisara Yunzai migration snapshot; notice version 0x⑨ | Repository revision 497fd9a, resource license blob; removed at 109cb82; no independent upstream release established | foods.json, chat_cute.csv, chat_tsundere.csv, chat_mixed.json | [legacy-LICENSE.txt](../src/kisara/resources/legacy-LICENSE.txt), [source/revision/hash](../src/kisara/resources/SOURCES.md#retained-notice-provenance); community attribution retained, no additional rights inferred |
| nonebot_plugin_tarot snapshot, 2026-09-23 | Source URL and tarot.json SHA-256 in resource SOURCES.md; no separate release version claimed | tarot.json/tarot_images.json; optional art stays ignored runtime data | [tarot-LICENSE.txt](../src/kisara/resources/tarot-LICENSE.txt), [source/hash](../src/kisara/resources/SOURCES.md) |

The preview renderer is project-authored, following an interface contract rather
than vendoring the installed skill script. No UUPM/Playwright material is retained.
Ordinary Python dependencies keep installed distribution notices.

Record unknown notice/provenance as `license-notice-needed` for affected material.
Do not invent an exact version, holder or NOTICE, or stage unresolved material
as reviewed. Continue independent work.
