# -*- coding: utf-8 -*-
{
    'name': 'TD Gauging',  # Nom commercial du module affiché dans les Apps
    'version': '18.0.1.0.0',  # Version de développement pour Odoo 18
    'category': 'Inventory',  # Catégorie standard Odoo
    'summary': 'Comprehensive management of fuel station gauging, tank inventory, and financial reconciliation.',  # Résumé
    'description': """
This project provides a professional tool for fuel station daily operations. 
It tracks tank inventory levels (inches/gallons) and pump meter readings assigned to employees. 
The module automates sales calculations and performs a full financial reconciliation 
between expected sales and counted amounts (Cash, Cards, Coupons, Checks, and Credit).
    """,  # Description détaillée du projet
    'author': 'Transition Digitale',  # Nom 
    'website': 'https://transitiondigitale.tech',  # Site internet 
    'depends': [  # Modules Odoo nécessaires au fonctionnement
        'base',  # Noyau Odoo
        'product',  # Gestion des carburants et des prix
        'hr',  # Gestion des employés/pompistes
    ],
    'data': [  # Liste des fichiers de configuration et de vues
        'security/ir.model.access.csv',  # Sécurité et droits d'accès
        'data/ir_sequence_data.xml',  # Configuration de la séquence ID
        'views/gauging_views.xml',  # Définition des interfaces List/Form
        'reports/gauging_reports.xml',  # Déclaration des actions d'impression
        'reports/gauging_report_templates.xml',  # Modèles de rapports QWeb PDF
    ],
    'installable': True,  # Permet l'installation du module
    'application': True,  # Définit le module comme une application à part entière
    'auto_install': False,  # Empêche l'installation automatique (Exigé)
    'license': 'LGPL-3',  # Type de licence standard
}