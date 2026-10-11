"""Application feature ownership and shared command exceptions.

Feature behavior and user-facing usage belong in each service module's opening
docstring. The tiny /ping and /help commands have no application service:
bot/commands/ping.py returns pong; bot/features.py owns the effective registry
and derived help, including feature switches/platform capabilities.
Telegram scheduled news is owned by news_push.py through a narrow async gateway
and infrastructure/persistence/telegram_news.py durable claims. Telegram commands
include ping/help/news/music and the Telegram-only /tgsetu native archive.
tgsetu.py owns private on/off activation, durable per-file jobs, caption/tag naming
and explicit failed-item retries; the Telegram adapter retrieves local SDK cache
paths, sends results and owns worker shutdown. The source adapter also uploads
captioned news PNG documents and music title/artist/links. /recall is a OneBot platform action implemented
in bot/dispatcher.py and bot/adapters/onebot_v11.py: it requires a quoted bot
message; a group caller must be an admin, owner, or KISARA_ADMIN_USERS member.
All commands still require the shared sender and, in groups, group allowlists.
Legacy aliases include ahelp for help and Chinese recall commands; consult the
dispatcher for the complete accepted spelling set.
"""
