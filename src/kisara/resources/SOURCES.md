# Bundled data sources

- `foods.json` came from the local Kisara Yunzai plugin snapshot. The original
  plugin license notice is preserved in `legacy-LICENSE.txt`.
- `chat_cute.csv` and `chat_tsundere.csv` are the two original CSV phrasebooks
  from that snapshot. The snapshot credited the community phrasebook shared at
  <https://mirai.mamoe.net/topic/1829/强大的二次元聊天机器人词库2w-词条-不定期更新>.
  The upstream source note described the phrasebooks as open and free. The
  original plugin's notice is preserved in `legacy-LICENSE.txt`.
- `chat_mixed.json` is the old generated reply pool. Its converter mixed the
  two source styles, so it is retained as an explicit compatibility option.
- `tarot.json` was downloaded from
  <https://github.com/MinatoAquaCrews/nonebot_plugin_tarot/blob/master/nonebot_plugin_tarot/tarot.json>
  on 2026-09-23. SHA-256:
  `8281c762c270ef8273fbaf9d362b66171b0a446fa0e947fbc25ed9f3d177ea9d`.
  The upstream plugin credits several sources for the card interpretations;
  its MIT license notice is preserved in `tarot-LICENSE.txt`. Only the card
  names, interpretations, and spread descriptions are bundled here. The legacy
  card images were kept as optional, ignored runtime data under
  `data/kisara/tarotCards` because the old plugin distributed them separately.
  `tarot_images.json` is a corrected image name index derived from that local
  directory; it fixes the duplicated magician variant and a priestess filename.

## Retained notice provenance

`legacy-LICENSE.txt` was restored byte-for-byte on 2026-10-09 from this
repository's migration revision `497fd9af0dc491cf0ba2fed1d3afc442acebd6c2` at
the same resource path (blob `a550d76e234a14e4b1e0e563c0c9bff8c1b39a0e`).
Revision `109cb82` had removed it while retained data/package metadata still
referred to it. SHA-256 of restored bytes:
`0d0db879c68fa00a0edadb41edd04f161251ee24931f474ff84c52a3fcb338ca`.
The multilingual RimoChan Revolution License, version `0x⑨`, retains its names,
placeholder year and CRLF bytes; it is not project-authored policy. Git history
is this collection's verified snapshot/version source, without an inferred
independent upstream release or additional community license.
The local resource .gitattributes preserves its exact bytes across Git newline
settings and treats the upstream notice's original spacing as intentional.

This is the migrated plugin's retained statement, not proof that every community
phrasebook contribution is covered by it. Preserve the community attribution
above. If distribution needs an additional notice not established by the source,
record `license-notice-needed` for that material instead of inventing permission.

See [the retained-material inventory](../../../third_party/index.md) for scoped
Trellis/resource notices. Ordinary Python dependencies retain package notices;
this collection does not vendor their source.
