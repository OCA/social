# Copyright 2023 ForgeFlow S.L. (www.forgeflow.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models


class MailThreadSubjectIgnore(models.Model):
    _name = "mail.thread.subject.ignore"
    _description = "Mail Thread Subject Ignore"

    name = fields.Text()
