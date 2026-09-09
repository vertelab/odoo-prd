# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2026 Vertel Sverige AB (<https://vertel.se>).
#    All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'PRD: AI',
    'version': '18.0.1.0.1',
    'summary': 'PRD-coworkers — PRD Analyst + PRD Module Builder',
    'category': 'Productivity',
    'description': """
        AI-medarbetare för Product Requirement Documents (PRD):
        analysera dokument, prioritera krav och designa Odoo-moduler
        från requirements. Bridge-modul (depends prd + ai_agent_core)
        enligt Vertel bridge-standard: ai.coworker + ai.tool + ai.skill
        som data-XML.
    """,
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-prd',
    'license': 'AGPL-3',
    'depends': [
        'prd',
        'ai_agent_core',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/prd_tools.xml',
        'data/prd_skills.xml',
        'data/prd_coworkers.xml',
        'views/session_views.xml',
    ],
    'demo': [],
    'application': False,
    'installable': True,
    'auto_install': False,
}
