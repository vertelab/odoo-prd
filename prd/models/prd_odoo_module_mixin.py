from datetime import datetime, timedelta
from github import Github, Auth
from odoo import api, fields, models, modules, tools, _
from odoo.addons.base.models.avatar_mixin import get_hsl_from_seed
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo.tools.misc import topological_sort, get_flag
from random import randint
from secrets import choice
import base64
import logging
import os
import re
import requests


_logger = logging.getLogger(__name__)
  
MANIFEST = """

name (str, required)
    the human-readable name of the module
    
version (str)
    this module’s version, should follow semantic versioning rules
    
summary
description (str)
    extended description for the module, in reStructuredText
    
author (str)
    name of the module author
    
website (str)
    website URL for the module author
    
license (str, defaults: LGPL-3)
    distribution license for the module. Possible values:
        GPL-2
        GPL-2 or any later version
        GPL-3
        GPL-3 or any later version
        AGPL-3
        LGPL-3
        Other OSI approved licence
        OEEL-1 (Odoo Enterprise Edition License v1.0)
        OPL-1 (Odoo Proprietary License v1.0)
        Other proprietary

category (str, default: Uncategorized)
    classification category within Odoo, rough business domain for the module.
    Although using existing categories is recommended, the field is freeform and unknown categories are created on-the-fly. Category hierarchies can be created using the separator / e.g. Foo / Bar will create a category Foo, a category Bar as child category of Foo, and will set Bar as the module’s category.

depends (list(str))
    Odoo modules which must be loaded before this one, either because this module uses features they create or because it alters resources they define.
    When a module is installed, all of its dependencies are installed before it. Likewise dependencies are loaded before a module is loaded.

data (list(str))
    List of data files which must always be installed or updated with the module. A list of paths from the module root directory
    
demo (list(str))
    List of data files which are only installed or updated in demonstration mode
    
auto_install (bool or list(str), default: False)
    If True, this module will automatically be installed if all of its dependencies are installed.
    It is generally used for “link modules” implementing synergetic integration between two otherwise independent modules.
    For instance sale_crm depends on both sale and crm and is set to auto_install. When both sale and crm are installed, it automatically adds CRM campaigns tracking to sale orders without either sale or crm being aware of one another.
    If it is a list, it must contain a subset of the dependencies. This module will automatically be installed as soon as all the dependencies in the subset are installed. The remaining dependencies will be automatically installed as well. If the list is empty, this module will always be automatically installed regardless of its dependencies and these will be installed as well.
    
external_dependencies (dict(key=list(str)))
    A dictionary containing python and/or binary dependencies.
    For python dependencies, the python key must be defined for this dictionary and a list of python modules to be imported should be assigned to it.
    For binary dependencies, the bin key must be defined for this dictionary and a list of binary executable names should be assigned to it.
    The module won’t be installed if either the python module is not installed in the host machine or the binary executable is not found within the host machine’s PATH environment variable.
    
application (bool, default: False)
    Whether the module should be considered as a fully-fledged application (True) or is just a technical module (False) that provides some extra functionality to an existing application module.
    
assets (dict)
    A definition of how all static files are loaded in various assets bundles. See the assets page for more details on how to describe bundles.
    
installable (bool default: True)
    Whether a user should be able to install the module from the Web UI or not.
    
maintainer (str)
    Person or entity in charge of the maintenance of this module, by default it is assumed that the author is the maintainer.
    
{pre_init, post_init, uninstall}_hook (str)
    Hooks for module installation/uninstallation, their value should be a string representing the name of a function defined inside the module’s __init__.py.
    pre_init_hook takes an env as its only argument, this function is executed prior to the module’s installation.
    post_init_hook takes an env as its only argument, this function is executed right after the module’s installation.
    uninstall_hook takes an env as its only argument, this function is executed after the module’s uninstallation.
    These hooks should only be used when setup/cleanup required for this module is either extremely difficult or impossible through the api.
    
"""
  
                    
class OdooModuleMixin(models.AbstractModel):
    _name = 'prd.odoo_module.mixin'
    _description = 'Odoo Module Mixin'

    active = fields.Boolean(string='Active', default=True)
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
    banner_image = fields.Binary(string='Banner', compute='_get_icon_image')
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
    # ~ url = fields.Char('URL', )
    sequence = fields.Integer('Sequence', default=100)
    # ~ dependency_ids = fields.Many2many(comodel_name='prd.odoo_module',string='_',help="") # relation|column1|column2
    dependency_ids = fields.One2many(  comodel_name='prd.odoo_module.dependency', 
                                        inverse_name='module_id',
                                        string='Dependencies',)
                                        
                                        

    
    # ~ icon_image = fields.Binary(string='Icon', compute='_get_icon_image')
    # ~ banner_image = fields.Binary(string='Banner', compute='_get_icon_image')
    # ~ icon_flag = fields.Char(string='Flag', compute='_get_icon_image',  inverse='_inverse_icon_flag')
    def _get_icon_image(self):
        for module in self:
            icon_image =  module.icon_image_file_id.content if module.icon_image_file_id else None
            banner_image =  module.banner_image_file_id.content if module.icon_image_file_id else None
            module.icon_flag = get_flag((self.module_id.get_module_info(module.name).get('countries', [])[0] or '').upper()) if len(self.module_id.get_module_info(module.name).get('countries', [])) == 1 else ''



    @api.model
    def _module2dict(self,module):
        fields = ["app_category_id","application","auto_install","author",
                  "contributors","description","description_html","icon",
                  "icon_image","licence_id","maintainer","name",
                  "summary","technical_name","website",'sequience',
                  'dependencies_ids',]
                                    
        return {field_name: module[field_name] 
                    for field_name in module.fields_get() if field_name in fields}
        
    @api.onchange('module_id')
    def _onchange_module_id(self):
        for record in self:
            if record.module_id and record._name == 'prd.document':
                for key, value in self._module2dict(record.module_id).items():
                    setattr(record, key, value)
                # ~ d = {field_name: record[field_name] for field_name in record.fields_get()}
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
            module.banner_image = False
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


class PrdDependency(models.Model):
    _name = 'prd.odoo_module.dependency'
    # ~ _inherit = "ir.module.module.dependency"
    _description = 'PRD dependencies for modules'

    module_id = fields.Many2one(comodel_name='prd.odoo_module',string="Module",help="")
    dep_module_id = fields.Many2one(comodel_name='prd.odoo_module',string="Depends",help="Module that is a dependency")

class PrdRule(models.Model):
    _name = 'prd.rule'
    _inherit = "ir.rule"
    _description = 'PRD rules for modules'

    prd_id = fields.Many2one(comodel_name="prd.document")
    # ~ group_ids = fields.One2many(comodel_name="prd.rule.groups",inverse_name="rule_id")
    
    groups = fields.Many2many( 
        comodel_name='res.groups',
        relation='prd_rule_group_rel',    
        column1='rule_id',           
        column2='group_id',            
        string='Groups'
    )
    

class PrdLicence(models.Model):
    _name = 'prd.odoo_licence'
    _description = 'PRD model licences'

    name = fields.Char(string='Licence')

class PrdModelAccess(models.Model):
    _name = 'prd.model.access'
    _inherit = "ir.model.access"
    _description = 'PRD model to set access rights for modules and models'

    prd_id = fields.Many2one(comodel_name="prd.document")
    
# ~ class PrdRuleGroups(models.Model):
    # ~ _name = 'prd.rule.groups'
    # ~ _description = 'Glue model for prd.rule and res.groups'

    # ~ rule_id = fields.Many2one(comodel_name="prd.rule")
    # ~ groups_id = fields.Many2one(comodel_name="res.groups")
    
    
class OdooBranch(models.Model):
    _name = 'prd.odoo_branch'
    _description = 'Odoo Branch'

    name = fields.Char(string='Name', required=True)


class OdooRepo(models.Model):
    _name = 'prd.odoo_repo'
    _description = 'Odoo Repository'

    name = fields.Char(string='Name', required=True)
    # ~ url = fields.Char(string='URL', help='url eg "https://api.github.com/repos/{self.owner}/{self.name}/git/trees/{branch_id.name}?recursive=1"')
    path = fields.Char(string='Path', help='Filesystem path')
    module_ids = fields.One2many(
        comodel_name='prd.odoo_module',
        inverse_name='repo_id',
        string='Modules',
        help=''
    )
    owner = fields.Char(string='Owner', size=64, trim=True, )
    repo_source = fields.Selection(selection=[('github','Github'),('gitlab','Gitlab')],string='Source')
    branch_ids = fields.Many2many(comodel_name='prd.odoo_branch',string='Branch',help="")
    
    @api.onchange("repo_source",'name','owner')
    def _repo_source(self):
        if self.repo_source == 'github':
            pass
            # ~ self.url = "f\"" + f"https://api.github.com/repos/{self.owner}/{self.name}/git/trees/" + "{branch_id.name}?recursive=1\""
    
    def _get_auth_token(self):
        authToken = self.env["ir.config_parameter"].sudo().get_param('prd.github_token')
        if not authToken:
            raise UserError("Github token missing, please create a parameter called github_token and paste an token.")
        return authToken

    def git_odoo_branches(self):
        g = Github(auth=Auth.Token(self._get_auth_token().strip()))
        try:
            repo_name = f"odoo/odoo" if self.owner == 'odoo' else f"{self.owner}/{self.name}"
            repo = g.get_repo(repo_name)
        except Exception as e:
            _logger.warning(f"Could not read {repo_name} {e}")
            return None
        for name in sorted([b.name for b in repo.get_branches() if re.match(r"^\d*[.]0$", b.name)], key=float):
            b = self.env['prd.odoo_branch'].search([('name','=',name)],limit=1)
            if not b:
                b = self.env['prd.odoo_branch'].create({'name': name})
            self.branch_ids = [(6,0,[b.id])]

    def _git_repo(self):
        g = Github(auth=Auth.Token(self._get_auth_token().strip()))
        try:
            repo_name = f"odoo/odoo" if self.owner == 'odoo' else f"{self.owner}/{self.name}"
            repo = g.get_repo(repo_name)
        except Exception as e:
            _logger.warning(f"Could not read {repo_name} {e}")
            raise
        return repo

    def get_files(self,filename, branch="14.0"):
        mfiles = []
        if self.owner == 'odoo':
            filename = f"addons/{filename}"
        try: 
            files = self._git_repo().get_contents(filename, ref=branch)
            if not isinstance(files, list):
                files=[files]
            _logger.warning(f"Read {files=}")
        except Exception as e:
            _logger.warning(f"Could not read  {filename=} {branch=} {self._git_repo()=} {e}")
            raise
            return []
        while files:
            file_content = files.pop(0)
            pos = 1 if self.owner != 'odoo' else 2
            if file_content.type == "dir" and "i18n" == path_list[pos] if len(path_list := file_content.path.split('/')) > pos else path_list[pos-1]:
                continue
            if file_content.type == "dir":
                files.extend(self._git_repo().get_contents(file_content.path,ref=branch))
            elif file_content.path not in ['.gitignore']:
                mfiles.append(file_content)
        p_files = set([f.path.replace('.p.','.') for f in mfiles if '.p.' in f.path and (f.path.endswith('.p.py') or f.path.endswith('.p.xml'))])
        # ~ _logger.warning(f"{mfiles=} {p_files=}\n\n{[f for f in mfiles if not f.path in p_files]=}")
        return [f for f in mfiles if not f.path in list(p_files)]

    def get_contents(self,filename,branch):
        try:
            content = self._git_repo().get_contents(filename,ref=branch)
        except Exception as e:
            content = f"{filename} Error {e}" 
        return content
    
    def get_file_content(self,filename,branch):
        _logger.warning(f"{filename=} {branch=}")
        try:
            content = self._git_repo().get_contents(filename,ref=branch)[0].decoded_content.decode('utf-8')
        except Exception as e:
            content = f"{filename} Error {e}" 
        return content

class OdooModule(models.Model):
    _name = 'prd.odoo_module'
    _inherit = ['prd.odoo_module.mixin', 'mail.thread', 'mail.activity.mixin', ]
    _description = 'Odoo Module'

    name = fields.Char(string='Name', required=True)
    branch_id = fields.Many2one(comodel_name='prd.odoo_branch',string="Branch",help="") # TODO Domain repo_id.branch_ids

    @api.model
    def get_modules(self):
        for mod in self.env['ir.module.module'].search([]):
            if self.search([('technical_name', '=', mod.name)], limit=1):
                continue
            vals = self._module2dict(mod)
            vals['technical_name'] = vals['name']
            vals['name'] = mod.shortdesc
            vals['module_id'] = mod.id
            vals['dependencies_id'] = [(6, 0, [x.id for x in vals['dependencies_id'] if x._name == 'ir.module.module' and x.id])]
            if not (hasattr(mod.dependencies_id, '_name') and mod.dependencies_id._name == 'ir.module.module.dependency'):
                vals['dependencies_id'] = None
            # ~ print(f"DEBUG: type(mod.dependencies_id) = {type(mod.dependencies_id)}") <class 'odoo.api.ir.module.module.dependency'>
            
            new_mod = self.create(vals)
            # ~ if mod.dependencies_id:
                # ~ new_mod.write({'dependencies_id': [(4, dep.id) for dep in mod.dependencies_id]})


    def sftp_upload(self):
        """Upload module directly to server via SFTP"""
        hostname = self.env.user.sftp_hostname
        port = self.env.user.sftp_port
        username = self.env.user.sftp_username

        if not hostname or not port or not username:
            raise UserError(
                f"One of the following values are not set on the user {self.env.user.name}\n\n"
                f"Hostname: {hostname}\nPort: {port}\nUsername: {username}"
            )

        if self.app_module.repo_id:
            module_path = f"/usr/share/{self.app_module.repo_id.name}/{self.app_module.technical_name}/"
        else:
            module_path = f"/usr/share/{self.name}/{self.app_module.technical_name}/"

        try:
            writer = SFTPFileWriter(
                username=username,
                hostname=hostname,
                port=port,
                module_path=module_path
            )
            self._build_module_structure(writer)
            writer.close()

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Module uploaded successfully to %s:%s%s') % (hostname, port, module_path),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f"SFTP upload failed: {str(e)}")
            raise UserError(f"Failed to upload module via SFTP:\n\n{str(e)}")




class OdooViewType(models.Model):
    _name = 'prd.odoo_view_type'
    _description = 'Odoo View Type'

    name = fields.Char(string='View Type Name', required=True)
    code = fields.Char(string='View Type Code', required=True)
    description = fields.Text(string='Description')
    prompt = fields.Text(string='Prompt')
    active = fields.Boolean(string='Active', default=True)

