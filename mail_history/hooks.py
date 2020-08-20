def post_init_hook(cr, registry):
    cr.execute(
        """WITH sub as (
            SELECT mail_message_id, res_partner_id
            FROM mail_message_res_partner_needaction_rel
        )
        INSERT INTO mail_message_res_partner_needaction_rel
            (mail_message_id, res_partner_id, is_read)
        SELECT mm.id, mmrpr.res_partner_id, True
        FROM mail_message mm
        JOIN mail_message_res_partner_rel mmrpr ON mmrpr.mail_message_id = mm.id
        WHERE mmrpr.res_partner_id NOT IN (
            SELECT res_partner_id FROM sub
        ) AND mm.id NOT IN (
            SELECT mail_message_id FROM sub
        )
        """
    )
