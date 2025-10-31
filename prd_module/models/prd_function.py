from datetime import datetime, timedelta 
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError
import logging

_logger = logging.getLogger(__name__)

class PrdFunction(models.Model):
    _inherit = 'prd.function'

    models_filename = fields.Char(string="Filename")
    models_inherit = fields.Char(string="Inherit")
    models_src = fields.Text(string="Models")
    controllers_filename = fields.Char(string="Filename")
    controllers_src = fields.Text(string="Controllers")
    data_filename = fields.Char(string="Filename")
    data_xml = fields.Text(string="Data")
    views_filename = fields.Char(string="Filename")
    views_xml = fields.Text(string="Views")
    summary = fields.Char(string='Summary', )
    
    
    has_controllers = fields.Boolean(string='Controllers')
    has_data = fields.Boolean(string='Data')
    has_models = fields.Boolean(string='Models')
    has_views = fields.Boolean(string='Views')
    is_inherit = fields.Boolean(string='Inherits')
    
    library_ids = fields.Many2many(comodel_name='prd.odoo_library',string='Libraries',help="")
    
    
class OdooBranches(models.Model):
    _name = 'prd.odoo_branches'
    _description = 'Odoo Branches'

    name = fields.Char(string='View Type Name', required=True)
    active = fields.Boolean(string='Active', default=True)

# ~ class OdooProject(models.Model):
    # ~ _name = 'prd.odoo_project'
    # ~ _description = 'Odoo Project'

    # ~ # requirement.txt / requirement.repo

    # ~ name = fields.Char(string='View Type Name', required=True)
    # ~ url = fields.Char(string='View Type Code', required=True)
    # ~ description = fields.Text(string='Description')
    # ~ active = fields.Boolean(string='Active', default=True)

class OdooLicence(models.Model):
    _name = 'prd.odoo_lincence'
    _description = 'Odoo Branches'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Licence Code', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)

# ~ class OdooModule(models.Model):
    # ~ _name = 'prd.odoo_module'
    # ~ _description = 'Odoo Module'

    # ~ # depends in __manifest__
    # ~ # requirement.repo
    
    # ~ name = fields.Char(string='Name', required=True)
    # ~ repo_id = fields.Many2one(comodel_name='prd.odoo_repo',string="Repo",help="")
    # ~ description = fields.Text(string='Description')
    # ~ active = fields.Boolean(string='Active', default=True)

# ~ class OdooRepo(models.Model):
    # ~ _name = 'prd.odoo_repo'
    # ~ _description = 'Odoo Repo'

    # ~ # depends in __manifest__
    # ~ # requirement.repo
    
    # ~ name = fields.Char(string='Name', required=True)
    # ~ url = fields.Char(string='Url', help="git@github.com:vertelab/odoo-contract.git")
    # ~ path = fields.Char(string='Url', help="/usr/share/odoo-contract",)
    # ~ description = fields.Text(string='Description')
    # ~ active = fields.Boolean(string='Active', default=True)

class OdooLibrary(models.Model):
    _name = 'prd.odoo_library'
    _description = 'Odoo Library'

    # requitement.txt

    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)

   
class OdooModels(models.Model):
    _name = 'prd.odoo_models'
    _description = 'Odoo Models'

    name = fields.Char(string='Name', required=True)
    active = fields.Boolean(string='Active', default=True)
