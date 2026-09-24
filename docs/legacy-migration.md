# Kisara legacy migration

The former `legacy-kisara-plugin/` directory was a historical snapshot, not a
runtime, build, or configuration dependency. It was removed locally after the
migration. Its reusable data is copied into the versioned Python package; source
and license information lives in `src/kisara/resources/SOURCES.md`. This record
is the feature inventory and the reference for deliberate behavior changes.

| Legacy area | Current home or decision |
| --- | --- |
| `data/foods.json`, `apps/main.js` food command | Packaged `foods.json`; `/eat` and Chinese food command aliases. |
| `data/chatLibrary`, `apps/chat.js`, `default/chat.chat.yaml` | Packaged original CSV phrasebooks and optional historical mixed JSON; exact and similar matching in `application/services/chat.py`. Settings and per-group overrides use `config/features/chat/config.toml`; environment variables and `config/groups.json` remain fallback inputs. |
| `apps/dice.js` | `/roll`, `/r`, `/dice` and old hash aliases. Multiple dice are independent draws; the old three-argument implementation sampled without replacement. Its TRPG methods were empty. |
| `apps/tarot.js`, `default/tarot.tarot.yaml`, `data/tarotCards` | `/tarot`, `占卜`, 78 card interpretations and spreads in the Python package; group spread probabilities in `config/features/tarot/config.toml`. The optional local card pictures live at `data/kisara/tarotCards` and are sent through OneBot. Readings are stable per user and China Standard Time day, including across restarts. The old `刷新占卜` reset a Redis daily lock; the new repeatable daily reading has no lock to reset, so that command is retired. |
| `apps/apis.js` | `/love`, `/source`, `/wallpaper`, `/music`, and `/ba` in `application/services/public.py`; image/music segments on OneBot. The old love endpoint failed and was replaced with TianAPI, which needs a key. Source search and music also need configured providers. |
| `apps/schedule.js` | `/news` renders the current provider's headlines to a dated local PNG cache. Optional daily push uses a persistent SQLite delivery record. Old delete-news remains retired; the new cache prunes expired images automatically. Manual `推送每日简报` is replaced by `/news` plus configured scheduled groups. |
| `apps/main.js` help and recall | `/help` and OneBot `/recall` of a quoted bot message; older `ahelp` and `撤回` aliases are accepted. |
| `utils/tools.js` | Only needed behavior is implemented within the new services, dispatcher, adapter, and config. Yunzai Redis keys, forwarded-message construction, and broad utility APIs are not needed by the new runtime. |
| `utils/gachaSupport.py` | An isolated probability prototype with no working bot command in the snapshot. It depends on historical game rules and is outside the migrated bot feature set. |
| `default/index.config.yaml` | Chat, tarot, news, source, music, and love settings each use `config/features/<name>/config.toml`; existing `.env` and `config/groups.json` values remain compatibility fallbacks. |

The old global per-command YAML switches and two-hour cooldown for some API
commands were not copied. The new bot uses user/group allowlists, global chat
and tarot switches, provider credentials, and bounded HTTP requests. A new
command-specific switch or cooldown can be added in Kisara if operations need
one; the old Yunzai configuration is not needed to do so.

The separately stored `05-kisara-plugin/data/tarotCards` directory contained
109 PNG files and a 78-card image manifest. The art was copied into the ignored
runtime directory `data/kisara/tarotCards`; a corrected image name index is
packaged in `tarot_images.json`. Card meanings and spreads already matched the
packaged deck. OneBot uses the local images when available; the official adapter
still returns text. The source repository described the art as collected from
the internet and distributed separately, so it is not included in the Python
package or Docker image. `{segment}` phrasebook replies are rendered as line breaks in a
single reply rather than separate delayed messages. Source search, music,
TianAPI, and real QQ send/recall behavior still need end-to-end verification
with configured credentials and an active OneBot account.

The source archive was ignored by Git and was not part of the Python wheel or
Docker image. Its removal did not remove any live Kisara feature or packaged
data.
