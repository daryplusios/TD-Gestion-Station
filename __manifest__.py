{
    'name': 'TD Gauging',  # Nom commercial du module
    'version': '18.0.1.0.0',  # Version compatible Odoo 18
    'category': 'Inventory',  # Catégorie technique pour le classement Odoo
    'summary': 'Comprehensive management of fuel station gauging, tank inventory, and financial reconciliation.',  # Résumé
    'description': 'The description of this module',  # Description détaillée exigée
    'author': 'Transition Digitale',  # Nom de l'auteur
    'website': 'https://transitiondigitale.tech',  # Site internet
    'depends': [  # Liste des modules nécessaires
        'base',  # Noyau Odoo
        'product',  # Requis pour les prix des carburants
        'hr',  # Requis pour les employés
        'stock',  # Requis pour intégrer les menus dans l'application Inventaire
    ],
    'data': [  # Chargement des fichiers XML
        'security/ir.model.access.csv',  # Sécurité des modèles
        'data/ir_sequence_data.xml',  # Numérotation automatique
        'views/gauging_views.xml',  # Interfaces utilisateur
        'reports/gauging_reports.xml',  # Actions d'impression
        'reports/gauging_report_templates.xml',  # Templates PDF
    ],
    'installable': True,  # Permet l'installation
    'application': True,  # Apparaît comme une application
    'auto_install': False,  # Pas d'installation automatique (Exigé)
    'license': 'LGPL-3',  # Licence standard
}