# Copyright 2022-2023 Moduon Team S.L. <info@moduon.team>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "Deferred Message Posting",
    "summary": "Faster and cancellable outgoing messages",
    "version": "16.0.1.0.1",
    "development_status": "Alpha",
    "category": "Productivity/Discuss",
    "website": "https://github.com/OCA/social",
    "author": "Moduon, Odoo Community Association (OCA)",
    "maintainers": ["Yajo"],
    "license": "LGPL-3",
    "depends": [
        "mail",
    ],
    "post_init_hook": "post_init_hook",
    "assets": {
        # This could go in mail.assets_messaging, but that's included in
        # mail.assets_discuss_public and we don't want the public to be able to
        # edit their messages; only the backend.
        "web.assets_backend": [
            "mail_post_defer/static/src/**/*.js",
        ],
    },
}
