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
  names, interpretations, and spread descriptions are bundled here. No card
  images were present in the local Kisara snapshot.
