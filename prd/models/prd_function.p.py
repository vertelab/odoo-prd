from datetime import datetime, timedelta 
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError
import logging

_logger = logging.getLogger(__name__)

class PrdFunction(models.Model):
    _name = 'prd.function'
    _inherit = ['mermaid.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'PRD Functions'

    # models / data / sequrity / sequirity.xml / views / 
    active = fields.Boolean(string='Active', default=True)
    category = fields.Many2many(
        comodel_name='prd.function_category',
        string='Tags',
        help="Categories"
    )
    description = fields.Text(string="Description")
    duration_tracking = fields.Float(string='Duration Tracking')
    func_type = fields.Many2one(comodel_name='prd.function_type', string="Type", help="")
    input_data = fields.Text(string="Input")
    module_id = fields.Many2one(comodel_name='prd.odoo_module',string="Odoo Module",help="")
    module_prd_id = fields.Many2one(comodel_name='prd.document',string="Product Requirement Document",help="")
    name = fields.Char(string="Name", required=True)
    odoo_view_ids = fields.Many2many(
        comodel_name='prd.odoo_view_type',
        string='View Types',
        help=""
    )
    output_data = fields.Text(string="Output")
    prd_id = fields.Many2one('prd.document', string='PRD', ondelete='cascade', required=True)
    process_data = fields.Text(string="Process")
    requirement_ids = fields.One2many(comodel_name='prd.requirement.function', inverse_name='func_id')
    sequence = fields.Integer(string='Sequence')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ongoing', 'Ongoing'),
        ('done', 'Done')
    ], string="State", default='draft')
    user_id = fields.Many2one(comodel_name='res.users', string="Author", help="")

class OdooView(models.Model):
    _name = 'prd.odoo_view'
    _description = 'Odoo View'

    func_id = fields.Many2one('prd.document', string='PRD', ondelete='cascade', required=True)
    view_type_id = fields.Many2one('prd.odoo_view_type', string='View Type', ondelete='cascade', required=True)
    prompt = fields.Text(string='Prompt')
    filename = fields.Char(string="Filename")
    source_code = fields.Text(string="Source Code")
    
    @api.onchange('view_type_id')
    def _onchange_view_type_id(self):
        if self.view_type_id:
            self.prompt = self.view_type_id.prompt or ''
        else:
            self.prompt = ''
            
class FunctionTypes(models.Model):
    _name = 'prd.function_type'
    _description = 'Function Type'

    name = fields.Char(string='Type', required=True)
    implementation_type = fields.Selection(selection=[('module','Module'),('prd','Product Requirement Document'),('other','Other')],string='Type',default="module",required=True)

class FunctionCategory(models.Model):
    _name = 'prd.function_category'
    _description = 'Function Category'

    name = fields.Char(string='Category', required=True)
    active = fields.Boolean(string='Active', default=True)

class OdooRepo(models.Model):
    _name = 'prd.odoo_repo'
    _description = 'Odoo Repository'

    name = fields.Char(string='Name', required=True)
    url = fields.Char(string='URL', help='Github url')
    path = fields.Char(string='Path', help='Filesystem path')
    module_ids = fields.One2many(
        comodel_name='prd.odoo_module',
        inverse_name='repo_id',
        string='Modules',
        help=''
    )

class OdooModule(models.Model):
    _name = 'prd.odoo_module'
    _description = 'Odoo Module'

    name = fields.Char(string='Name', required=True)
    technical_name = fields.Char(string='Technical Name', required=True)
    module_id = fields.Many2one(comodel_name='ir.module.module',string="Module",help="")
    repo_id = fields.Many2one(comodel_name='prd.odoo_repo',string="Repo",help="")
    application = fields.Boolean(string='Application')

    @api.onchange('module_id')
    def _onchange_module_id(self):
        for record in self:
            if record.module_id:
                record.technical_name = record.module_id.name
                record.name = record.module_id.shortdesc or record.module_id.name
                record.application = record.module_id.application
                record.repo_id = self.env.ref('prd.repo_odoo') if 'Odoo S.A.' in record.module_id.author else None
                
    @api.model
    def get_modules(self):
        for mod in self.env['ir.module.module'].search([]):
            if self.search([('technical_name', '=', mod.name)], limit=1):
                continue
            self.create({
                'name': mod.shortdesc or mod.name,
                'technical_name': mod.name,
                'module_id': mod.id,
                'application': mod.application,
                'repo_id': ref('prd.repo_odoo') if 'Odoo' in mod.author else None,
            })
    
class OdooViewType(models.Model):
    _name = 'prd.odoo_view_type'
    _description = 'Odoo View Type'

    name = fields.Char(string='View Type Name', required=True)
    code = fields.Char(string='View Type Code', required=True)
    description = fields.Text(string='Description')
    prompt = fields.Text(string='Prompt')
    active = fields.Boolean(string='Active', default=True)
