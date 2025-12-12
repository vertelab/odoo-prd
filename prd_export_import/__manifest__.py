{
    'name': 'PRD Export Import',
    'version': '18.0.1.0.0',
    'category': 'prd',
    'summary': 'Export and import PRD easily',
    'depends': ['website_slides'],
    'data': [
        'security/ir.model.access.csv',
        'views/export_import_wizard_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
