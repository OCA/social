# Copyright 2019 Alexandre Díaz
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).


from openupgradelib.openupgrade import migrate


@migrate()
def migrate(env, version):
    cr = env.cr
    cr.execute("UPDATE mail_tracking_email SET token = NULL")
