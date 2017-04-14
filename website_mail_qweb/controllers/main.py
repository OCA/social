# -*- coding: utf-8 -*-
# © 2017 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp.addons.website_mail.controllers.email_designer import\
    WebsiteEmailDesigner
from openerp import http
from openerp.http import request


class UnquoteObject(str):
    def __getattr__(self, name):
        return UnquoteObject('%s.%s' % (self, name))

    def __repr__(self):
        return self

    def __call__(self, *args, **kwargs):
        return UnquoteObject(
            '%s(%s)' % (
                self,
                ','.join(
                    [
                        UnquoteObject(
                            a if not isinstance(a, basestring)
                            else "'%s'" % a
                        )
                        for a in args
                    ] +
                    [
                        '%s=%s' % (UnquoteObject(k), v)
                        for (k, v) in kwargs.iteritems()
                    ]
                )
            )
        )


class Main(WebsiteEmailDesigner):
    @http.route()
    def index(self, model, res_id, template_model=None, **kw):
        result = super(Main, self).index(
            model, res_id, template_model=template_model, **kw
        )
        qcontext = result.qcontext
        record = qcontext['record']
        if record.body_type == 'qweb':
            qcontext['body_field'] = 'body_view_id'
            qcontext['mode'] = 'email_designer'
            qcontext['object'] = UnquoteObject('object')
            qcontext['email_template'] = record
        return result
