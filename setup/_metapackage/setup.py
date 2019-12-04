import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo13-addons-oca-social",
    description="Meta package for oca-social Odoo addons",
    version=version,
    install_requires=[
        'odoo13-addon-mail_activity_board',
        'odoo13-addon-mail_optional_autofollow',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
