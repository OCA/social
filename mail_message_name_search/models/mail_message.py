# -*- coding: utf-8 -*-
# © 2016 Eficent Business and IT Consulting Services S.L.
#   (http://www.eficent.com)
# © 2016 Serpent Consulting Services Pvt. Ltd. (<http://www.serpentcs.com>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from openerp import api, models
from lxml import etree
from openerp.osv import expression


_base_fields_view_get = models.BaseModel.fields_view_get


@api.model
def _custom_fields_view_get(self, view_id=None, view_type='form',
                            toolbar=False, submenu=False):
    # Tricky super call
    res = _base_fields_view_get(self, view_id=view_id, view_type=view_type,
                                toolbar=toolbar, submenu=submenu)
    if view_type == 'search' and self._fields.get('message_ids'):
        doc = etree.XML(res['arch'])
        for node in doc.xpath("//field[1]"):
            elem = etree.Element('field', {
                'name': 'message_ids',
                'domain': "[('model','=', %s)]" % self._model
            })
            node.addnext(elem)
            res['fields'].update({
                'message_ids': {
                    'type': 'many2one',
                    'relation': 'mail.message',
                    'string': 'Messages',
                }
            })
            res['arch'] = etree.tostring(doc)
    return res


models.BaseModel.fields_view_get = _custom_fields_view_get


class MailMessage(models.Model):

    _inherit = 'mail.message'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        domain = ['|', '|', ('record_name', operator, name),
                  ('subject', operator, name), ('body', operator, name)]
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            domain = domain[2:]
        rec = self.search(domain + args, limit=limit)
        return rec.name_get()
