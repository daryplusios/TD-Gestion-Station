{
    'name': 'TD Gauging',  # Nom commercial
    'version': '18.0.1.0.0',  # Version Odoo 18
    'category': 'Inventory',  # Catégorie pour le classement
    'summary': 'Comprehensive management of fuel station gauging, tank inventory, and financial reconciliation.',  # Résumé
    'description': 'The description of this module',  # Description
    'author': 'Transition Digitale',  # Auteur exigé
    'website': 'https://transitiondigitale.tech',  # Website exigé
    'depends': ['base', 'product', 'hr'],  # Dépendances minimales (Base, Articles, Employés)
    'data': [  # Ordre de chargement des fichiers XML
        'security/ir.model.access.csv',  # Sécurité
        'data/ir_sequence_data.xml',  # Séquence ID
        'views/gauging_views.xml',  # Vues et Menus
        'reports/gauging_report_templates.xml',  # Design rapports
        'reports/gauging_reports.xml',  # Déclaration rapports
    ],
    'installable': True,  # Autorise l'installation
    'application': True,  # INDISPENSABLE pour apparaître sur le Dashboard principal
    'auto_install': False,  # Empêche l'installation automatique
    'license': 'LGPL-3',  # Licence
}