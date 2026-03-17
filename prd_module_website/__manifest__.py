# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2025- Vertel AB (<https://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'PRD Module Website',
    'version': '1.0',
    'summary': 'Website interface for listing PRD modules and repositories',
    'category': 'Website',
    'description': """
        Website Module for PRD
        =======================
        
        This module provides a website interface to browse and view PRD repositories and modules.
        
        Features:
        - List all PRD repositories
        - Browse modules within each repository
        - View detailed module information including manifest and files
    """,
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-prd/prd_module_website',
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'depends': ['prd_module', 'website'],
    'data': [
        'views/templates.xml',
    ],
    'application': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
