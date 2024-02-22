import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo-addons-oca-social",
    description="Meta package for oca-social Odoo addons",
    version=version,
    install_requires=[
        'odoo-addon-base_search_mail_content>=16.0dev,<16.1dev',
        'odoo-addon-email_template_qweb>=16.0dev,<16.1dev',
        'odoo-addon-mail_activity_board>=16.0dev,<16.1dev',
        'odoo-addon-mail_activity_done>=16.0dev,<16.1dev',
        'odoo-addon-mail_activity_partner>=16.0dev,<16.1dev',
        'odoo-addon-mail_activity_reminder>=16.0dev,<16.1dev',
        'odoo-addon-mail_activity_team>=16.0dev,<16.1dev',
        'odoo-addon-mail_attach_existing_attachment>=16.0dev,<16.1dev',
        'odoo-addon-mail_autosubscribe>=16.0dev,<16.1dev',
        'odoo-addon-mail_composer_cc_bcc>=16.0dev,<16.1dev',
        'odoo-addon-mail_composer_cc_bcc_account>=16.0dev,<16.1dev',
        'odoo-addon-mail_debrand>=16.0dev,<16.1dev',
        'odoo-addon-mail_drop_target>=16.0dev,<16.1dev',
        'odoo-addon-mail_improved_tracking_value>=16.0dev,<16.1dev',
        'odoo-addon-mail_layout_preview>=16.0dev,<16.1dev',
        'odoo-addon-mail_optional_autofollow>=16.0dev,<16.1dev',
        'odoo-addon-mail_optional_follower_notification>=16.0dev,<16.1dev',
        'odoo-addon-mail_outbound_static>=16.0dev,<16.1dev',
        'odoo-addon-mail_partner_opt_out>=16.0dev,<16.1dev',
        'odoo-addon-mail_post_defer>=16.0dev,<16.1dev',
        'odoo-addon-mail_quoted_reply>=16.0dev,<16.1dev',
        'odoo-addon-mail_restrict_follower_selection>=16.0dev,<16.1dev',
        'odoo-addon-mail_send_confirmation>=16.0dev,<16.1dev',
        'odoo-addon-mail_show_follower>=16.0dev,<16.1dev',
        'odoo-addon-mail_template_substitute>=16.0dev,<16.1dev',
        'odoo-addon-mail_tracking>=16.0dev,<16.1dev',
        'odoo-addon-mail_tracking_mailgun>=16.0dev,<16.1dev',
        'odoo-addon-mail_tracking_mass_mailing>=16.0dev,<16.1dev',
        'odoo-addon-mass_mailing_contact_active>=16.0dev,<16.1dev',
        'odoo-addon-mass_mailing_event_registration_exclude>=16.0dev,<16.1dev',
        'odoo-addon-mass_mailing_list_dynamic>=16.0dev,<16.1dev',
        'odoo-addon-mass_mailing_partner>=16.0dev,<16.1dev',
        'odoo-addon-mass_mailing_resend>=16.0dev,<16.1dev',
        'odoo-addon-mass_mailing_unique>=16.0dev,<16.1dev',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 16.0',
    ]
)
