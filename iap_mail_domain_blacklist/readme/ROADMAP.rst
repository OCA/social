Due to a technical limitation, http.db_list() cannot be used during module
loading to respect dbfilter, because the HTTP layer is not initialized at
that stage. As a result, the module must rely on config.get('db_name') or
db.list_dbs() instead. Consequently, if list_db = True is enabled without
explicitly setting db_name in odoo.conf, blacklist domains from inactive
databases may incorrectly affect active databases.
