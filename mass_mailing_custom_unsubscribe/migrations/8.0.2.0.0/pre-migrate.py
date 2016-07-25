# -*- coding: utf-8 -*-
# © 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

try:
    from openupgradelib.openupgrade import rename_xmlids
except ImportError:
    # Simplified version mostly copied from openupgradelib
    def rename_xmlids(cr, xmlids_spec):
        for (old, new) in xmlids_spec:
            if '.' not in old or '.' not in new:
                raise Exception(
                    'Cannot rename XMLID %s to %s: need the module '
                    'reference to be specified in the IDs' % (old, new))
            else:
                query = ("UPDATE ir_model_data SET module = %s, name = %s "
                         "WHERE module = %s and name = %s")
                cr.execute(query, tuple(new.split('.') + old.split('.')))


def migrate(cr, version):
    """Update database from previous versions, before updating module."""
    rename_xmlids(
        cr,
        (("website.mass_mail_unsubscription_" + r,
          "mass_mailing_custom_unsubscribe." + r)
         for r in ("success", "failure")))
