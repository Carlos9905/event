# -*- coding: utf-8 -*-
{
    'name': 'Event Management',
    'version': '15.0.1.0.0',
    'summary': """Módulo central para la gestión de diferentes tipos de eventos.""",
    'description': """Módulo central para la gestión de diferentes tipos de eventos.""",
    'author': 'Jose Aguilar',
    'company': 'Jose Aguilar',
    'maintainer': 'Jose Aguilar',
    'depends': ['product', 'account', 'sale_management'],
    'data': ['security/event_security.xml',
             'security/ir.model.access.csv',
             'views/event_management_view.xml',
             'views/event_type_view.xml',
             'views/dashboard.xml',
             'data/event_management.xml',
             'reports/event_management_pdf_report.xml',
             'reports/pdf_report_template.xml',
             'wizards/event_management_wizard.xml',
             ],
    'assets': {
        'web.assets_backend': [
            "event_management/static/src/css/event_dashboard.css",
            "event_management/static/src/js/action_manager.js"
        ],
    },
    'installable': True,
    'application': True,
}
