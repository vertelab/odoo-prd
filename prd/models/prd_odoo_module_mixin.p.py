from datetime import datetime, timedelta 
from odoo import api, fields, models, modules, tools, _
from odoo.addons.base.models.avatar_mixin import get_hsl_from_seed
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo.tools.misc import topological_sort, get_flag
from random import randint
from secrets import choice
import base64
import logging
import os

_logger = logging.getLogger(__name__)
  
                    
class OdooModuleMixin(models.AbstractModel):
    _name = 'prd.odoo_module.mixin'
    _description = 'Odoo Module Mixin'


    app_category_id = fields.Many2one('ir.module.category', string="Category")
    application = fields.Boolean(string='Application')
    auto_install = fields.Boolean('Automatic Installation',
        help='An auto-installable module is automatically installed by the '
             'system when all its dependencies are satisfied. '
             'If the module has no dependency, it is always installed.')
    author = fields.Char("Author")
    contributors = fields.Text('Contributors')
    description = fields.Text(string='Description')
    description_html = fields.Html(string='Index')
    icon = fields.Char(string='Icon URL')
    icon_image = fields.Binary(string='Icon', compute='_get_icon_image')
    icon_flag = fields.Char(string='Flag', compute='_get_icon_image',  inverse='_inverse_icon_flag')
    licence_id = fields.Many2one(comodel_name='prd.odoo_licence', string="Licence", help="")
    maintainer = fields.Char('Maintainer')
    model_access_ids = fields.One2many(comodel_name="prd.model.access", inverse_name="prd_id")
    module_id = fields.Many2one(comodel_name='ir.module.module', string="Module", help="")
    repo_id = fields.Many2one(comodel_name='prd.odoo_repo', string="Repo", help="")
    rule_ids = fields.One2many(comodel_name="prd.rule", inverse_name="prd_id")
    summary = fields.Char(string='Summary')
    technical_name = fields.Char(string='Technical Name')
    website = fields.Char(string='Website')

    @api.model
    def _module2dict(self,module):
        fields = ["app_category_id","application","auto_install","author",
                  "contributors","description","description_html","icon",
                  "icon_image","licence_id","maintainer",
                  "summary","technical_name","website"]
                  
        return {field_name: module[field_name] 
                    for field_name in module.fields_get() if field_name in fields}
        
    @api.onchange('module_id')
    def _onchange_module_id(self):
        for record in self:
            if record.module_id:
                d = {field_name: record[field_name] for field_name in record.fields_get()}
                # ~ raise UserError(f"{d}")            
            if record.module_id and record._name != 'prd.document':
                for key, value in self._module2dict(record.module_id).items():
                    setattr(record, key, value)

    # ~ @api.depends('icon')
    def _get_icon_image(self):
        self.icon_image = ''
        for module in self:
            if not module.id:
                continue
            if module.icon:
                path = os.path.join(module.icon.lstrip("/"))
            else:
                path = modules.module.get_module_icon_path(module)
            if path:
                try:
                    with tools.file_open(path, 'rb', filter_ext=('.png', '.svg', '.gif', '.jpeg', '.jpg')) as image_file:
                        module.icon_image = base64.b64encode(image_file.read())
                except FileNotFoundError:
                    module.icon_image = ''
            countries = self.module_id.get_module_info(module.name).get('countries', [])
            country_code = len(countries) == 1 and countries[0]
            # ~ module.icon_flag = get_flag(country_code.upper()) if country_code else ''


    def _inverse_icon_flag(self):
        for record in self:
            record.icon_flag = record.icon_flag
            
            # ~ if record.icon_flag == 'no-icon':
                # ~ record.icon = False
                # ~ record.icon_image = False
            # ~ elif record.icon_flag == 'has-icon-url':
                # ~ record.icon_image = False  # Rensa bild om URL väljs
            # ~ elif record.icon_flag == 'has-icon-image':
                # ~ record.icon = False  # Rensa URL om bild väljs

class PrdRule(models.Model):
    _name = 'prd.rule'
    _inherit = "ir.rule"
    _description = 'PRD rules for modules'

    prd_id = fields.Many2one(comodel_name="prd.document")
    groups = fields.One2many(comodel_name="prd.rule.groups",inverse_name="rule_id")

class PrdLicence(models.Model):
    _name = 'prd.odoo_licence'
    _description = 'PRD model licences'

    name = fields.Char(string='Licence')

class PrdModelAccess(models.Model):
    _name = 'prd.model.access'
    _inherit = "ir.model.access"
    _description = 'PRD model to set access rights for modules and models'

    prd_id = fields.Many2one(comodel_name="prd.document")
    
class PrdRuleGroups(models.Model):
    _name = 'prd.rule.groups'
    _description = 'Glue model for prd.rule and res.groups'

    rule_id = fields.Many2one(comodel_name="prd.rule")
    groups_id = fields.Many2one(comodel_name="res.groups")
