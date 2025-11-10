from odoo import models, fields

class IrModel(models.Model):
    _inherit = 'ir.model'

    include_mail_history = fields.Boolean(string='Include Mail History in Notifications', default=False, help='If enabled, email notifications for records of this model will include the previous chatter discussion.')