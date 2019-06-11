# Copyright 2019 Eficent <http://www.eficent.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).


def migrate(cr, version):
    if not version:
        return
    cr.execute("""
        UPDATE mail_activity SET
            active = False
            WHERE done=True;
    """)
