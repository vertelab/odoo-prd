{
    'website': 'https://vertel.se/apps/odoo-prd/prd_export_import',
    'name': 'PRD Export Import',
    'version': '18.0.1.0.0',
    'license': 'AGPL-3',
    'category': 'prd',
    'summary': 'Export and import PRD easily.',
    'description': '''
PRD Export Import
=================

    Export and import PRD easily.

    Features:

        - Guided Wizards: Step-by-step dialogs for data entry.
        - UI Integration: Extends 2 view(s) in the Odoo interface.
    ''',
    'depends': ['prd', 'prd_scrum'],
    'data': [
        'security/ir.model.access.csv',
        'views/export_import_wizard_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
