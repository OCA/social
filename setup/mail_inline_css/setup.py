import setuptools

setuptools.setup(
    setup_requires=['setuptools-odoo'],
    odoo_addon= {'external_dependencies_override': {
            'python': {
                'premailer': 'premailer<=3.6.2'
            },
        },
    }
)
