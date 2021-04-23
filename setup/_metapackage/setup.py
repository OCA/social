import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo10-addons-oca-social",
    description="Meta package for oca-social Odoo addons",
    version=version,
    install_requires=[
        'odoo10-addon-base_search_mail_content',
        'odoo10-addon-bus_presence_override',
        'odoo10-addon-email_template_qweb',
        'odoo10-addon-mail_as_letter',
        'odoo10-addon-mail_attach_existing_attachment',
        'odoo10-addon-mail_check_mailbox_size',
        'odoo10-addon-mail_debrand',
        'odoo10-addon-mail_digest',
        'odoo10-addon-mail_drop_target',
        'odoo10-addon-mail_embed_image',
        'odoo10-addon-mail_follower_custom_notification',
        'odoo10-addon-mail_footer_notified_partner',
        'odoo10-addon-mail_force_queue',
        'odoo10-addon-mail_forward',
        'odoo10-addon-mail_full_expand',
        'odoo10-addon-mail_improved_tracking_value',
        'odoo10-addon-mail_inline_css',
        'odoo10-addon-mail_notify_bounce',
        'odoo10-addon-mail_optional_autofollow',
        'odoo10-addon-mail_optional_follower_notification',
        'odoo10-addon-mail_outbound_static',
        'odoo10-addon-mail_restrict_follower_selection',
        'odoo10-addon-mail_sendgrid',
        'odoo10-addon-mail_sendgrid_mass_mailing',
        'odoo10-addon-mail_tracking',
        'odoo10-addon-mail_tracking_mailgun',
        'odoo10-addon-mail_tracking_mass_mailing',
        'odoo10-addon-mass_mailing_custom_unsubscribe',
        'odoo10-addon-mass_mailing_event',
        'odoo10-addon-mass_mailing_list_dynamic',
        'odoo10-addon-mass_mailing_partner',
        'odoo10-addon-mass_mailing_resend',
        'odoo10-addon-mass_mailing_unique',
        'odoo10-addon-website_mass_mailing_name',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
