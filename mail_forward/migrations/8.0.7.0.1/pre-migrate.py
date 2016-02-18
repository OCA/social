# -*- coding: utf-8 -*-
# © 2016 Grupo ESOC Ingeniería de Servicios, S.L.U. - Jairo Llopis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

try:
    from openerp.addons import migratk

    @migratk.manage
    def migrate(cr, version):
        """Update database from previous versions, before updating module."""
        mail_forward = migratk.Migrator(cr, "mail_forward")
        mail_forward._table_constraint_remove(
            "mail_forward_compose_message",
            "mail_forward_compose_message_original_wizard_id_fkey")
        mail_forward.model_remove("mail_forward.compose.message", False)

except ImportError:
    # If you get here, it means that you don't need the migration
    def migrate(cr, version):
        pass
