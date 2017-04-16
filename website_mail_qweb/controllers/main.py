# -*- coding: utf-8 -*-
# © 2017 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp.addons.website_mail.controllers.email_designer import\
    WebsiteEmailDesigner
from openerp import http
from openerp.http import request


class UnquoteRecordset(object):
    def __init__(self, recordset, name):
        self.__recordset = recordset
        self.__name = name

    def __getitem__(self, key):
        if isinstance(key, basestring) and key in self.__recordset._fields:
            return self.__recordset[key]
        return UnquoteRecordset(
            self.__recordset[key], '%s[%s]' % (self.__name, key)
        )

    def __getattr__(self, name):
        recordset = self.__recordset
        if name in recordset._fields:
            if recordset._fields[name].relational:
                return UnquoteRecordset(
                    recordset[name], '%s.%s' % (self.__name, name)
                )
            elif recordset._fields[name].type in ('char', 'text'):
                return '%s.%s' % (self.__name, name)
            elif recordset._fields[name].type in ('integer', 'float'):
                return 42
            else:
                return recordset[name]
        return getattr(recordset, name)


class Main(WebsiteEmailDesigner):
    @http.route()
    def index(self, model, res_id, template_model=None, **kw):
        result = super(Main, self).index(
            model, res_id, template_model=template_model, **kw
        )
        env = request.env
        qcontext = result.qcontext
        record = qcontext.get('record', env['email.template'].new())
        if record.body_type == 'qweb':
            qcontext['body_field'] = 'body_view_id'
            qcontext['mode'] = 'email_designer'
            qcontext['object'] = UnquoteRecordset(
                env[record.model_id.model].new(),
                'object',
            )
            qcontext['email_template'] = record
        return result
