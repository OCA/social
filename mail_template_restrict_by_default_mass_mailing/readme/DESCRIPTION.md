By default, all Odoo backend users are members of the group `Mass mailing / User`,
which allows editing dynamic templates. This in turn allows to run code, which allows to
escalate privileges.

This module removes the default assignment, and removes the mass mailing user group from all users except admin.
