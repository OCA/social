from odoo import tools, api, fields, models

# Copy Odoo's implementation in v12 back to v10 so that we have useful hooks to add what we need to later on.


class CrmActivityReportOdoo(models.Model):
    _inherit = 'crm.activity.report'

    def _select(self):
        return """
               SELECT
                    m.id,
                    m.subtype_id,
                    m.author_id,
                    m.date,
                    m.subject,
                    l.id as lead_id,
                    l.user_id,
                    l.team_id,
                    l.country_id,
                    l.company_id,
                    l.stage_id,
                    l.partner_id,
                    l.type as lead_type,
                    l.active,
                    l.probability
           """

    def _from(self):
        return """
               FROM mail_message AS m
           """

    def _join(self):
        return """
               JOIN crm_lead AS l ON m.res_id = l.id
           """

    def _where(self):
        return """
               WHERE
                   m.model = 'crm.lead'
           """

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
               CREATE OR REPLACE VIEW %s AS (
                   %s
                   %s
                   %s
                   %s
               )
           """ % (self._table, self._select(), self._from(), self._join(), self._where())
                         )
