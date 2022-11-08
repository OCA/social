import setuptools

setuptools.setup(
    setup_requires=['setuptools-odoo'],
    odoo_addon={
        'external_dependencies_override': {
            'python': {
                'extract_msg': 'extract_msg<0.30',
            },
        },
    },
    install_requires=[
        'extract_msg<0.30'
    ],
)
