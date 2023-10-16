# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# Copyright 2018 David Vidal - <david.vidal@tecnativa.com>
# Copyright 2018 Tecnativa - Ernesto Tejeda
# Copyright 2019 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Email tracking",
    "summary": "Email tracking system for all mails sent",
    "version": "16.0.1.0.1",
    "category": "Social Network",
    "website": "https://github.com/OCA/social",
    "author": ("Tecnativa, " "Odoo Community Association (OCA)"),
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": ["mail"],
    "data": [
        "data/tracking_data.xml",
        "security/mail_tracking_email_security.xml",
        "security/ir.model.access.csv",
        "views/mail_tracking_email_view.xml",
        "views/mail_tracking_event_view.xml",
        "views/mail_message_view.xml",
        "views/res_partner_view.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mail_tracking/static/src/client_actions/failed_message_storage.esm.js",
            "mail_tracking/static/src/models/chatter.esm.js",
            "mail_tracking/static/src/models/discuss_sidebar_mailbox_view.esm.js",
            "mail_tracking/static/src/models/discuss_view.esm.js",
            "mail_tracking/static/src/models/mailbox.esm.js",
            "mail_tracking/static/src/models/message_list_view_item.esm.js",
            "mail_tracking/static/src/models/message_list_view.esm.js",
            "mail_tracking/static/src/models/message_view.esm.js",
            "mail_tracking/static/src/models/message.esm.js",
            "mail_tracking/static/src/models/messaging_initializer.esm.js",
            "mail_tracking/static/src/models/messaging.esm.js",
            "mail_tracking/static/src/models/thread.esm.js",
            "mail_tracking/static/src/components/discuss/discuss.xml",
            "mail_tracking/static/src/components/message/message.xml",
            "mail_tracking/static/src/components/message/message.esm.js",
            "mail_tracking/static/src/components/message/message.scss",
            "mail_tracking/static/src/components/message_list/message_list.esm.js",
            "mail_tracking/static/src/components/failed_message/failed_message.xml",
            "mail_tracking/static/src/components/failed_message/failed_message.esm.js",
            "mail_tracking/static/src/components/failed_message/failed_message.scss",
            "mail_tracking/static/src/components/failed_message_list/failed_message_list.xml",
            "mail_tracking/static/src/components/failed_message_list/failed_message_list.esm.js",  # noqa: B950
            "mail_tracking/static/src/components/discuss_sidebar_mailbox/discuss_sidebar_mailbox.xml",  # noqa: B950
            "mail_tracking/static/src/components/discuss_sidebar_mailbox/discuss_sidebar_mailbox.esm.js",  # noqa: B950
            "mail_tracking/static/src/components/thread_view/thread_view.xml",
            "mail_tracking/static/src/components/thread_view/thread_view.scss",
        ],
    },
    "demo": ["demo/demo.xml"],
}
