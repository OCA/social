# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def post_init_hook(cr, registry):
    cr.execute(
        """
        UPDATE mailing_contact_list_rel
        SET subscription_date = create_date
        WHERE NOT opt_out
        """
    )
