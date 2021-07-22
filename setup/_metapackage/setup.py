import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo14-addons-oca-social",
    description="Meta package for oca-social Odoo addons",
    version=version,
    install_requires=[
        'odoo14-addon-base_search_mail_content',
        'odoo14-addon-email_template_qweb',
        'odoo14-addon-mail_attach_existing_attachment',
        'odoo14-addon-mail_debrand',
        'odoo14-addon-mail_layout_preview',
        'odoo14-addon-mail_outbound_static',
        'odoo14-addon-mail_preview_base',
        'odoo14-addon-mail_restrict_send_button',
        'odoo14-addon-mail_send_copy',
        'odoo14-addon-mail_tracking',
        'odoo14-addon-mass_mailing_partner',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
