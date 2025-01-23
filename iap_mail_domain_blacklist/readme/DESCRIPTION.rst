This module allows adding domains to the mail domain blacklist to prevent Odoo from assuming  
that users with the same domain belong to the same organization.

Blacklisted domains are shared across all effective databases on the server.
When the db_name parameter is set, the effective databases are assumed to be the
values of that parameter. If db_name is not set and list_db is true, all
databases on the instance are considered effective databases.
