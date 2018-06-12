# -*- coding: utf-8 -*-
{
    'name':'Activities board',
    "version": "11.0.1.0.1",
    'category':'',
    'author':['David Juaneda', 'Javier Garcia'],
    'description': """
This is a full-featured crm system.
========================================

It supports:
------------

    - Board activities with form, tree, kanban, graph, calendar and pivot views and different filters.

    """,
    'license':'GPL-3',
    'depends':[
                'crm','mail','board',
               ],
    'data':[
            'views/activities_boards_views.xml',
            'views/inherit_crm_opportunities_views.xml',
            ],
    'qweb': [

             ],
    'demo':[],
    'installable':True,
}
