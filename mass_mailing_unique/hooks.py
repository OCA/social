# Copyright 2015 Grupo ESOC Ingeniería de Servicios, S.L.U. - Jairo Llopis
# Copyright 2016 Tecnativa - Vicent Cubells
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _
from odoo.exceptions import ValidationError


def pre_init_hook(cr):
    """Make sure there are no duplicates before installing the module.

    If you define an unique key in Odoo that cannot be applied, Odoo will log a
    warning and install the module without that constraint. Since this module
    is useless without those constraints, we check here if all will work before
    installing, and provide a user-friendly message in case of failure.
    """
    errors = list()
    # Search for duplicates in emails
    cr.execute(
        """
          SELECT email_normalized, COUNT(id) as count
          FROM mailing_contact
          GROUP BY email_normalized
          HAVING COUNT(id) > 1
      """
    )
    for result in cr.fetchall():
        errors.append(
            "There are {1} mailing contacts with the same email: {0}".format(*result)
        )
    # Search for duplicates in list's name
    cr.execute(
        """
          SELECT name, COUNT(id) as count
          FROM mailing_list
          GROUP BY name
          HAVING COUNT(id) > 1
      """
    )
    for result in cr.fetchall():
        errors.append(
            "There are {1} mailing lists with the same name: {0}.".format(*result)
        )
    # Abort if duplicates are found
    if errors:
        raise ValidationError(
            _("Unable to install module mass_mailing_unique:\n%s", "\n".join(errors))
        )
