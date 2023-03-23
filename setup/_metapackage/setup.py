import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo-addons-oca-social",
    description="Meta package for oca-social Odoo addons",
    version=version,
    install_requires=[
        'odoo-addon-mail_activity_board>=16.0dev,<16.1dev',
        'odoo-addon-mail_attach_existing_attachment>=16.0dev,<16.1dev',
        'odoo-addon-mail_debrand>=16.0dev,<16.1dev',
        'odoo-addon-mail_optional_autofollow>=16.0dev,<16.1dev',
        'odoo-addon-mail_optional_follower_notification>=16.0dev,<16.1dev',
        'odoo-addon-mail_outbound_static>=16.0dev,<16.1dev',
        'odoo-addon-mail_partner_opt_out>=16.0dev,<16.1dev',
        'odoo-addon-mass_mailing_contact_active>=16.0dev,<16.1dev',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 16.0',
    ]
)
