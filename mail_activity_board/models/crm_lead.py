# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# SDI
# author: djuaneda@sdi.es
from odoo import api, fields, models, _


class Lead(models.Model):
    _inherit = 'crm.lead'

    opportunity_activities_count = fields.Integer(
        "Activities", compute='_compute_activities_count')

    @api.multi
    def _compute_activities_count(self):
        """
        Calculates the number of activities related to the opportunity
        """
        for opp in self:
            opp.opportunity_activities_count = self.env['mail.activity']\
                .search_count([('res_model', '=', 'crm.lead'),
                               ('res_id', '=', opp.id)])
            if 'active' in self.env['mail.activity']._fields:
                opp.opportunity_activities_count += self.env['mail.activity']\
                    .search_count([('res_model', '=', 'crm.lead'),
                                   ('res_id', '=', opp.id),
                                   ('active', '=', False)])

    def redirect_to_lead_actvivities(self):
        """
            Method that redirects to the list of opportunity activities.
            :return: action.
        """
        action = self.env['mail.activity'].action_your_activities()
        action['name'] = _('Opportunity\'s activities')
        action['domain'] = [('res_id', '=', self.id)]
        return action
