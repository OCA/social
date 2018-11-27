# Copyright 2018 Eficent Business and IT Consulting Services, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class MailActivityTeam(models.Model):
    _name = "mail.activity.team"
    _description = 'Mail Activity Team'

    name = fields.Char(string='Name', required=True, translate=True)
    active = fields.Boolean(string='Active', default=True)
    res_model_ids = fields.Many2many('ir.model', string='Used models')
    member_ids = fields.Many2many('res.users', 'mail_activity_team_users_rel',
                                  string="Team Members")
