import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo12-addons-oca-social",
    description="Meta package for oca-social Odoo addons",
    version=version,
    install_requires=[
        'odoo12-addon-base_search_mail_content',
        'odoo12-addon-email_template_qweb',
        'odoo12-addon-mail_activity_done',
        'odoo12-addon-mail_activity_partner',
        'odoo12-addon-mail_attach_existing_attachment',
        'odoo12-addon-mail_debrand',
        'odoo12-addon-mail_track_diff_only',
        'odoo12-addon-mail_tracking',
        'odoo12-addon-mail_tracking_mailgun',
        'odoo12-addon-mail_tracking_mass_mailing',
        'odoo12-addon-mass_mailing_resend',
        'odoo12-addon-mass_mailing_unique',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
