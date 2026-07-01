import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    env.cr.execute("""
        UPDATE res_partner rp
            SET social_mastodon = rc.social_mastodon
            FROM res_company rc
            WHERE rc.partner_id = rp.id
            AND rc.social_mastodon is not null;
        """)
