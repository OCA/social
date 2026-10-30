# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from urllib.parse import quote

# Scopes no call of this module requires. The Community Management migration
# guide maps, since June 2023, ``r_organization_social`` to
# ``r_organization_social_feed`` and ``w_organization_social`` to
# ``w_organization_social_feed`` for the reactions and the social actions.
# That migration is about the versioned ``/rest`` resources, and the comments
# and the reactions of this module speak ``/v2``, where the permissions the
# application already holds are enough: measured against a real page on
# 2026-08-24, ``POST /rest/socialActions/{urn}/comments`` answers
# ``403 ACCESS_DENIED`` on ``partnerApiSocialActions.CREATE`` — the Partner
# Program, not a scope — while ``POST /v2/socialActions/{urn}/comments``
# publishes the comment. They are the road to follow the day ``/v2`` stops
# answering.
_SCOPE_OPTIONAL_SYNC_LINKEDIN = [
    "r_organization_social_feed",
    "w_organization_social_feed",
]

# The prefix of the URN LinkedIn names a member with. It is the actor of a
# comment that cannot be resolved into a name: the Profile API only answers
# for the authenticated member, and the token of the connector belongs to the
# organization. Comments signed by one of these are drawn with a neutral
# label, never with the name of the account reading the thread.
_URN_PERSON_LINKEDIN = "urn:li:person:"

# The prefix of the URN naming an uploaded video, which is what tells a
# publication carrying one apart while the feed is read back.
_URN_VIDEO_LINKEDIN = "urn:li:video:"

# A comment is addressed by a composite URN, the thread it lives on plus its
# own identifier: urn:li:comment:(urn:li:activity:6666,120381273128).
_URN_COMMENT_LINKEDIN = "urn:li:comment:"

# Which figures of a daily bucket are watched, by their position in the tuple
# ``_get_linkedin_daily_statistics`` builds: clicks, likes, comments, shares
# and impressions. The engagement (position 4) is left out on purpose: it is a
# ratio of the other figures over the impressions, so it cannot move without
# one of them moving, and it is the only float of the set.
_UPDATE_CHECK_FIGURES_LINKEDIN = (0, 1, 2, 3, 5)

# How many pages of the feed one pass reads. The Posts API answers at most
# ``_POSTS_PAGE_SIZE_LINKEDIN`` posts per page, so the default covers five
# thousand publications. It is not a limit of LinkedIn: it is what keeps a feed
# that never ends from looping forever, and it is the number an account with a
# longer history has to raise, because a feed read short comes back partial and
# a partial feed is one the pass will not look for deletions in.
_POSTS_MAX_PAGES_LINKEDIN = 50
_POSTS_MAX_PAGES_MIN_LINKEDIN = 1
_POSTS_MAX_PAGES_MAX_LINKEDIN = 500

# What is asked for of the organization behind a comment. Narrower than the
# projection the association reads, because a comment only needs the name to
# write and the logo to draw: the vanity name names nothing on screen. The
# logo travels as the URL of a playable stream and is drawn from there, so
# nothing is downloaded to show a thread.
_PROJECTION_ACTOR_LINKEDIN = "(id,name,logoV2(original~:playableStreams))"


def linkedin_reaction_id(actor, entity):
    """Return the key naming the reaction of one actor on one entity.

    The Reactions API addresses a single reaction by the pair that creates
    it, ``(actor:...,entity:...)``. The parentheses, the comma between the
    two fields and the colons that name them are Rest.li syntax and travel
    raw; the URNs they carry are opaque strings, so theirs are escaped.

    :param actor: URN of the person or the organization holding the reaction.
    :param entity: URN of the share, UGC post or comment reacted to.
    :rtype: str
    """
    return f"(actor:{quote(actor, safe='')},entity:{quote(entity, safe='')})"
