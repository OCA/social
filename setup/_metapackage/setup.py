import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo13-addons-oca-social",
    description="Meta package for oca-social Odoo addons",
    version=version,
    install_requires=[
        'odoo13-addon-email_template_qweb',
        'odoo13-addon-mail_activity_board',
        'odoo13-addon-mail_activity_done',
        'odoo13-addon-mail_inline_css',
        'odoo13-addon-mail_optional_autofollow',
        'odoo13-addon-mail_tracking',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
