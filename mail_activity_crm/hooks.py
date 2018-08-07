# Copyright 2018 Eficent Business and IT Consulting Services S.L.
# Copyright 2018 Tecnativa, S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from openerp import api, SUPERUSER_ID


def convert_crm_activity_types(env):
    """Point default crm.activity.type records to their equivalents now in v11,
    and create the rest manually."""
    column_name = "crm_activity"
    table = 'mail_activity_type'
    column = 'crm_activity'
    env.cr.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s AND column_name = %s""", (table, column))
    if not bool(env.cr.fetchall()):
        env.cr.execute(
            "ALTER TABLE mail_activity_type ADD COLUMN crm_activity INTEGER")

    type_mapping = {
        'crm.crm_activity_data_email':
            'mail_activity.mail_activity_data_email',
        'crm.crm_activity_data_call':
            'mail_activity.mail_activity_data_call',
        'crm.crm_activity_data_meeting':
            'mail_activity.mail_activity_data_todo',
    }
    migrated_ids = []
    for old_xml_id, new_xml_id in type_mapping.items():
        env.cr.execute(
            "SELECT res_id FROM ir_model_data "
            "WHERE module = %s and name = %s",
            (old_xml_id.split('.')[0], old_xml_id.split('.')[1]),
        )
        row = env.cr.fetchone()
        if row:
            old_id = row[0]
            migrated_ids.append(old_id)
            env.cr.execute(
                "UPDATE mail_activity_type "
                "SET %s = %s WHERE id = %s"
                % (column_name, old_id, env.ref(new_xml_id).id)
            )
    env.cr.execute("""
        INSERT INTO mail_activity_type
            (name, sequence, res_model_id, category, days,
             create_date, create_uid, write_uid, write_date, %s)
        SELECT
            mms.name, ca.sequence, im.id, 'default', ca.days,
            ca.create_date, ca.create_uid, ca.write_uid, ca.write_date, ca.id
        FROM
            crm_activity AS ca,
            mail_message_subtype AS mms,
            ir_model AS im
        WHERE
             mms.id = ca.subtype_id AND
             im.model = 'crm.lead' AND
             ca.id NOT IN %s
        """ % (column_name, tuple(migrated_ids), )
    )


def convert_crm_lead_activities(env):
    """Create mail.activity records for the corresponding activities in v10."""
    column_name = 'crm_activity'
    env.cr.execute("""
        INSERT INTO mail_activity
            (res_id, res_model_id, res_model, res_name, summary,
             activity_type_id, date_deadline, create_uid, create_date,
             write_uid, write_date, user_id)
         SELECT
            cl.id,  im.id, 'crm.lead', cl.name, cl.title_action,
            mat.id, cl.date_action, cl.create_uid, cl.create_date,
            cl.write_uid, cl.write_date, COALESCE(cl.user_id, cl.create_uid)
         FROM
            crm_lead AS cl,
            mail_activity_type AS mat,
            ir_model AS im
         WHERE
            next_activity_id IS NOT NULL AND
            date_action IS NOT NULL AND
            im.model = 'crm.lead' AND
            mat.%s = cl.next_activity_id
         """ % (column_name, )
    )


def delete_crm_activities(env):
    """Delete old activities in order to avoid duplicating them
    when we transition to v11."""
    env.cr.execute("""
        DELETE FROM crm_activity
    """)


def post_init_hook(cr, registry):
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        convert_crm_activity_types(env)
        convert_crm_lead_activities(env)
        delete_crm_activities(env)
