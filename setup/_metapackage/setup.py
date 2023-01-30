import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo-addons-oca-social",
    description="Meta package for oca-social Odoo addons",
    version=version,
    install_requires=[
        'odoo-addon-base_search_mail_content>=15.0dev,<15.1dev',
        'odoo-addon-mail_activity_board>=15.0dev,<15.1dev',
        'odoo-addon-mail_activity_creator>=15.0dev,<15.1dev',
        'odoo-addon-mail_activity_done>=15.0dev,<15.1dev',
        'odoo-addon-mail_activity_partner>=15.0dev,<15.1dev',
        'odoo-addon-mail_activity_team>=15.0dev,<15.1dev',
        'odoo-addon-mail_attach_existing_attachment>=15.0dev,<15.1dev',
        'odoo-addon-mail_autosubscribe>=15.0dev,<15.1dev',
        'odoo-addon-mail_debrand>=15.0dev,<15.1dev',
        'odoo-addon-mail_notification_custom_subject>=15.0dev,<15.1dev',
        'odoo-addon-mail_optional_autofollow>=15.0dev,<15.1dev',
        'odoo-addon-mail_optional_follower_notification>=15.0dev,<15.1dev',
        'odoo-addon-mail_outbound_static>=15.0dev,<15.1dev',
        'odoo-addon-mail_parent_recipient>=15.0dev,<15.1dev',
        'odoo-addon-mail_preview_base>=15.0dev,<15.1dev',
        'odoo-addon-mail_quoted_reply>=15.0dev,<15.1dev',
        'odoo-addon-mail_show_follower>=15.0dev,<15.1dev',
        'odoo-addon-mail_tracking>=15.0dev,<15.1dev',
        'odoo-addon-mail_tracking_mailgun>=15.0dev,<15.1dev',
        'odoo-addon-mass_mailing_custom_unsubscribe>=15.0dev,<15.1dev',
        'odoo-addon-mass_mailing_partner>=15.0dev,<15.1dev',
        'odoo-addon-mass_mailing_resend>=15.0dev,<15.1dev',
        'odoo-addon-microsoft_outlook_single_tenant>=15.0dev,<15.1dev',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 15.0',
    ]
)
