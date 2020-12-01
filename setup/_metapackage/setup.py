import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo13-addons-oca-social",
    description="Meta package for oca-social Odoo addons",
    version=version,
    install_requires=[
        'odoo13-addon-base_search_mail_content',
        'odoo13-addon-email_template_qweb',
        'odoo13-addon-fetchmail_thread_default',
        'odoo13-addon-mail_activity_board',
        'odoo13-addon-mail_activity_done',
        'odoo13-addon-mail_activity_team',
        'odoo13-addon-mail_attach_existing_attachment',
        'odoo13-addon-mail_debrand',
        'odoo13-addon-mail_drop_target',
        'odoo13-addon-mail_full_expand',
        'odoo13-addon-mail_inline_css',
        'odoo13-addon-mail_optional_autofollow',
        'odoo13-addon-mail_optional_follower_notification',
        'odoo13-addon-mail_outbound_static',
        'odoo13-addon-mail_preview_audio',
        'odoo13-addon-mail_preview_base',
        'odoo13-addon-mail_restrict_follower_selection',
        'odoo13-addon-mail_tracking',
        'odoo13-addon-mail_tracking_mailgun',
        'odoo13-addon-mail_tracking_mass_mailing',
        'odoo13-addon-mass_mailing_custom_unsubscribe',
        'odoo13-addon-mass_mailing_custom_unsubscribe_event',
        'odoo13-addon-mass_mailing_event_registration_exclude',
        'odoo13-addon-mass_mailing_list_dynamic',
        'odoo13-addon-mass_mailing_partner',
        'odoo13-addon-mass_mailing_resend',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
