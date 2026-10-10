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

# The media types X serves as a video file. X answers an animated GIF as a
# single mp4 too, so both are downloaded the same way, from their variants:
# neither carries the ``url`` a photo has.
_VIDEO_MEDIA_TYPES_X = ("video", "animated_gif")

# The content type of the variants Odoo can play. The other variant X lists,
# ``application/x-mpegURL``, is an HLS playlist that needs a player of its own.
_VIDEO_CONTENT_TYPE_X = "video/mp4"

# How many of the latest likes of the account one read asks for. A hundred is
# the ceiling of the endpoint, and a single page is read: X charges every post
# it answers, so walking the pages would make the cost grow with the history
# of the account. A like older than the hundred latest is not seen.
_LIKED_TWEETS_MAX_RESULTS_X = 100

# The context key with which the client asks for the comments of a dialog
# already open. Those comments keep the like the dialog read when it opened,
# so the refresh does not pay a page of likes again.
_SKIP_LIKES_CONTEXT_X = "social_x_skip_likes"


def _strip_media_links_x(text, entities):
    """Remove from the text of a tweet the links X adds for its media.

    X ends the text of a tweet with an image, a video or a GIF with a
    ``https://t.co/…`` link that points at the media. In ``entities.urls`` the
    entry of that link carries a ``media_key``; the entry of a link the author
    wrote, or of the tweet a quote points at, does not, so those stay in the
    text as X wrote them.

    :param text: the text of the tweet, as X answered it.
    :param entities: the ``entities`` of the tweet, or ``None`` when X sent
        none.
    :return: the text without the links of its media, otherwise unchanged.
    :rtype: str
    """
    for url in (entities or {}).get("urls") or []:
        if url.get("media_key") and url.get("url"):
            text = text.replace(url["url"], "")
    return text
