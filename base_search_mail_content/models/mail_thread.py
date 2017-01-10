# -*- coding: utf-8 -*-
# © 2016 Eficent Business and IT Consulting Services S.L.
#   (http://www.eficent.com)
# © 2016 Serpent Consulting Services Pvt. Ltd. (<http://www.serpentcs.com>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from openerp import api, fields, models
from lxml import etree
from openerp.osv import expression
from openerp.osv.orm import setup_modifiers


class MailThread(models.AbstractModel):

    _inherit = 'mail.thread'

    def _search_message_content(self, operator, value):
        domain = [('model', '=', self._name), '|', '|',
                  ('record_name', operator, value),
                  ('subject', operator, value), ('body', operator, value)]

        if operator in expression.NEGATIVE_TERM_OPERATORS:
            domain = domain[2:]
        recs = self.env['mail.message'].search(domain)
        return [('id', 'in', recs.mapped('res_id'))]

    @api.multi
    def _compute_message_content(self):
        """ We don't really need to show any content. This field is to be
        used only by searches"""
        return ''

    message_content = fields.Text(
        string='Messages',
        help='Message content, to be used only in searches',
        compute="_compute_message_content",
        search='_search_message_content')


_base_fields_view_get = models.BaseModel.fields_view_get


@api.model
def _custom_fields_view_get(self, view_id=None, view_type='form',
                            toolbar=False, submenu=False):
    """
    Override to add message_ids field in all the objects
    that inherits mail.thread
    """
    # Tricky super call
    res = _base_fields_view_get(self, view_id=view_id, view_type=view_type,
                                toolbar=toolbar, submenu=submenu)
    if view_type == 'search' and self._fields.get('message_content'):
        doc = etree.XML(res['arch'])
        res['fields'].update({
            'message_content': {
                'type': 'char',
                'string': 'Message content',
            }
        })

        for node in doc.xpath("//field[1]"):
            # Add message_ids in search view
            elem = etree.Element('field', {
                'name': 'message_content',
            })
            setup_modifiers(elem)
            node.addnext(elem)
            res['arch'] = etree.tostring(doc)
    return res


models.BaseModel.fields_view_get = _custom_fields_view_get
