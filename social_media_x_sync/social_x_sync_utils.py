# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

# How many replies one page of the conversation asks for. A hundred is the
# ceiling of the recent search endpoint. X charges the replies it answers,
# not the request that asked for them, so a page of a hundred costs the same
# as the ten pages of ten it saves. Without it X applies its own default of
# ten, and a thread of eleven replies is read wrong.
_SEARCH_MAX_RESULTS_X = 100

# How many pages of one conversation are walked. Five hundred replies is
# already an extraordinary thread, and the ceiling is what keeps a single
# dialog from spending the quota of the whole database: the dialog refreshes
# itself every two minutes while it stays open, and every refresh asks X for
# the conversation again. X charges a reply once per 24 hours however many
# times it is read, so a dialog left open pays for the replies that arrive,
# not for the thread it already holds.
_COMMENTS_MAX_PAGES_X = 5
