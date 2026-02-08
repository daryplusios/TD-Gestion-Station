{
    'name': 'TD Gauging',  # Nom commercial du module
    'version': '18.0.1.0.0',  # Version compatible Odoo 18
    'category': 'Operations',  # Catégorie de l'application dans Odoo
    'summary': 'Comprehensive management of fuel station gauging, tank inventory, and financial reconciliation.',  # Résumé des fonctionnalités
    'description': """
This project provides a professional tool for fuel station daily operations. 
It tracks tank inventory levels (inches/gallons) and pump meter readings assigned to employees. 
The module automates sales calculations and performs a full financial reconciliation 
between expected sales and counted amounts (Cash, Cards, Coupons, Checks, and Credit).
    """,
    'author': 'Transition Digitale',  # Nom de l'auteur exigé
    'website': 'https://transitiondigitale.tech',  # Site web exigé
    'depends': [  # Dépendances nécessaires au module
        'base',  # Noyau Odoo
        'product',  # Gestion des carburants et prix
        'hr',  # Gestion des employés/pompistes
    ],
    'data': [  # Fichiers XML à charger
        'security/ir.model.access.csv',  # Sécurité et droits d'accès
        'data/ir_sequence_data.xml',  # Séquence de numérotation automatique
        'views/gauging_views.xml',  # Vues List et Form
        'reports/gauging_reports.xml',  # Déclaration des actions de rapports
        'reports/gauging_report_templates.xml',  # Templates de rapports QWeb
    ],
    'installable': True,  # Autorise l'installation du module
    'application': True,  # Définit le module comme une application métier
    'auto_install': False,  # Empêche l'installation automatique (exigé)
    'license': 'LGPL-3',  # Licence standard Odoo
}