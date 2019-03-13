# -*- coding: utf-8 -*-
# Copyright 2019 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models, exceptions, _


class MailReferenceMention(models.Model):
    _name = 'mail.reference.mention'

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, "Delimiter: %s, Shown At: %s Shows: %s" % (
                rec.delimiter,
                ', '.join(rec.shown_at_model_ids.mapped('name')),
                rec.shows_model_id.name
            )))
        return res

    delimiter = fields.Char(
        help='The string that when input on the chatter '
             'will signify a reference.',
        size=1,
    )

    @api.constrains('delimiter', 'shown_at_model_ids')
    def _constrain_unique_delimiter_per_model(self):
        for rec in self:
            if rec.delimiter == '#':
                raise exceptions.ValidationError(_(
                    'Cannot use # as delimiter, its already used for channel'))
            if self.search_count([
                    ('delimiter', '=', rec.delimiter),
                    ('shown_at_model_ids', 'in', rec.shown_at_model_ids.ids),
                    ]) > 1:
                raise exceptions.ValidationError(_(
                    'Single delimiter per model.'))

    def _get_domain_mail_thread_inheritants(self):
        """ We are only interested in the models that actually have a chatter
        along with a name field for us to search for.
        """
        model_mail_thread = self.env['mail.thread'].sudo()
        model_ir_model = self.env['ir.model'].sudo()
        model_names = [
            x for x in model_mail_thread.pool.descendants(
                ['mail.thread'],
                '_inherit')
        ]
        model_ids = model_ir_model.search([
            ('model', 'in', model_names),
            ('field_id.name', 'in', ['name', 'x_name'])]).ids
        return [('id', 'in', model_ids)]

    shown_at_model_ids = fields.Many2many(
        'ir.model',
        string='Shown At',
        domain=_get_domain_mail_thread_inheritants,
        help='The models that this delimiter will appear on',
    )
    shows_model_id = fields.Many2one(
        'ir.model',
        string='Shows',
        domain=_get_domain_mail_thread_inheritants,
        help='The model that this delimeter will show records of'
    )
    shows_model_id_name = fields.Char(
        related='shows_model_id.model',
        store=True,
    )

    @api.depends('shown_at_model_ids')
    def _compute_model_names(self):
        for rec in self:
            rec.model_names = ','.join(rec.shown_at_model_ids.mapped('model'))

    model_names = fields.Char(compute='_compute_model_names', store=True)
