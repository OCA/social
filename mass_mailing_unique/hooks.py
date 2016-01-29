# -*- coding: utf-8 -*-
# © 2015 Grupo ESOC Ingeniería de Servicios, S.L.U. - Jairo Llopis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import _
from openerp.exceptions import ValidationError


def pre_init_hook(cr):
    """Make sure there are no duplicates before installing the module.

    If you define a unique key in Odoo that cannot be applied, Odoo will log a
    warning and install the module without that constraint. Since this module
    is useless without those constraints, we check here if all will work before
    installing, and provide a user-friendly message in case of failure.
    """
    errors = list()

    # Search for duplicates in emails
    cr.execute("""SELECT c.email, l.name, COUNT(c.id)
                  FROM
                    mail_mass_mailing_contact AS c
                    INNER JOIN mail_mass_mailing_list AS l ON c.list_id = l.id
                  GROUP BY l.name, l.id, c.email
                  HAVING COUNT(c.id) > 1""")
    for result in cr.fetchall():
        errors.append(
            _("{0} appears {2} times in list {1}.").format(*result))

    # Search for duplicates in list's name
    cr.execute("""SELECT name, COUNT(id)
                  FROM mail_mass_mailing_list
                  GROUP BY name
                  HAVING COUNT(id) > 1""")
    for result in cr.fetchall():
        errors.append(
            _("There are {1} lists with name {0}.").format(*result))

    # Abort if duplicates are found
    if errors:
        raise ValidationError(
            _("Fix this before installing:") +
            "".join("\n" + e for e in errors))
