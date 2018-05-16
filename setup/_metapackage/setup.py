import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo11-addons-oca-social",
    description="Meta package for oca-social Odoo addons",
    version=version,
    install_requires=[
        'odoo11-addon-email_template_qweb',
        'odoo11-addon-mail_debrand',
        'odoo11-addon-mail_digest',
        'odoo11-addon-mail_restrict_follower_selection',
        'odoo11-addon-mail_tracking',
        'odoo11-addon-mail_tracking_mailgun',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
