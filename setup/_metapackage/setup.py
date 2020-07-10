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
        'odoo13-addon-mail_activity_board',
        'odoo13-addon-mail_activity_done',
        'odoo13-addon-mail_activity_team',
        'odoo13-addon-mail_debrand',
        'odoo13-addon-mail_inline_css',
        'odoo13-addon-mail_optional_autofollow',
        'odoo13-addon-mail_restrict_follower_selection',
        'odoo13-addon-mail_tracking',
        'odoo13-addon-mail_tracking_mailgun',
        'odoo13-addon-mail_tracking_mass_mailing',
        'odoo13-addon-mass_mailing_partner',
        'odoo13-addon-mass_mailing_resend',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
