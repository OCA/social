import setuptools

setuptools.setup(
    setup_requires=['setuptools-odoo'],
    odoo_addon={
        'external_dependencies_override': {
            'python': {
                'extract_msg': 'extract_msg<=0.29.6',
            },
        },
    }
)
