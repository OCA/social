By default, all Odoo backend users are members of the group `Mail Template Editor`,
which allows editing dynamic templates. This in turn allows to run code, which allows to
escalate privileges.

Checking `Restrict mail templates edition and QWEB placeholders usage` in the general
settings fixes this, but as that's a manual and therefore error prone action, this
module automates this. It also removes all users except admin from the edit group.
