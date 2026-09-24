"""Application feature ownership and shared command exceptions.

Feature behavior and user-facing usage belong in each service module's opening
docstring. The tiny /ping and /help commands have no application service:
bot/commands/ping.py returns pong, while bot/commands/help.py lists commands
whose dependencies are enabled. /recall is a OneBot platform action implemented
in bot/dispatcher.py and bot/adapters/onebot_v11.py: it requires a quoted bot
message; a group caller must be an admin, owner, or KISARA_ADMIN_USERS member.
All commands still require the shared sender and, in groups, group allowlists.
Legacy aliases include ahelp for help and Chinese recall commands; consult the
dispatcher for the complete accepted spelling set.
"""
