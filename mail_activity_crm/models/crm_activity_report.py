from odoo import api, fields, models


class CrmActivityReport(models.Model):
    _inherit = 'crm.activity.report'

    mail_activity_type_id = fields.Many2one('mail.activity.type', 'Activity Type', readonly=True)

    def _select(self):
        select = super(CrmActivityReport, self)._select()
        return select + """
                   , m.mail_activity_type_id
        """

    def _where(self):
        where = super(CrmActivityReport, self)._where()
        return where + """
             --   AND m.mail_activity_type_id IS NOT NULL
        """
