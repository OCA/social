import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo9-addons-oca-social",
    description="Meta package for oca-social Odoo addons",
    version=version,
    install_requires=[
        'odoo9-addon-base_search_mail_content',
        'odoo9-addon-email_template_qweb',
        'odoo9-addon-fetchmail_thread_default',
        'odoo9-addon-mail_as_letter',
        'odoo9-addon-mail_attach_existing_attachment',
        'odoo9-addon-mail_debrand',
        'odoo9-addon-mail_digest',
        'odoo9-addon-mail_improved_tracking_value',
        'odoo9-addon-mail_optional_autofollow',
        'odoo9-addon-mail_optional_follower_notification',
        'odoo9-addon-mail_tracking',
        'odoo9-addon-mail_tracking_mailgun',
        'odoo9-addon-mail_tracking_mass_mailing',
        'odoo9-addon-mass_mailing_custom_unsubscribe',
        'odoo9-addon-mass_mailing_partner',
        'odoo9-addon-mass_mailing_security_group',
        'odoo9-addon-mass_mailing_unique',
        'odoo9-addon-website_livechat_firstname',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 9.0',
    ]
)
