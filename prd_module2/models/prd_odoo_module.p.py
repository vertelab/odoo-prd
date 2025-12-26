from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError
import logging
import filetype
import base64
from github.ContentFile import ContentFile

_logger = logging.getLogger(__name__)

class OdooModule(models.Model):
    _inherit = 'prd.odoo_module'

    files_count = fields.Integer(string="Total Files", compute='_compute_file_counts',store=True)
    file_ids = fields.One2many('prd.odoo_module.file', 'module_id', string="Files")
    branch_id = fields.Many2one(comodel_name='prd.odoo_branch',string="Branch",help="")
    
    @api.depends('file_ids')
    def _compute_file_counts(self):
        for record in self:
            record.files_count = len(record.file_ids)

    def button_get_module_files(self):
        self.ensure_one()
        if not all([self.repo_id, self.repo_id.owner, self.branch_id]):
            raise UserError(_("Missing repo, branch or owner"))
        files = self.repo_id.get_files(self.technical_name,self.branch_id.name)
        self.message_post(
            body=_(f"Get Module files {files=}"),
            subtype_xmlid="mail.mt_note",  # intern anteckning
        )
        for file in files:
            self.env['prd.odoo_module.file']._create_update(file,self)
        return self.action_files()

    def action_files(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Files',
            'res_model': 'prd.odoo_module.file',  
            'domain': [('module_id', '=', self.id)],
            'context': {'default_module_id': self.id},
            'view_mode': 'kanban,list,form',
            'target': 'current',
        }
        
    def get_files(self):
        for m in self:
            self.env['prd.odoo_module.file'].get_modules_files(m)

class OdooModuleFile(models.Model):
    _name = 'prd.odoo_module.file'
    _description = 'Files within a module'
    
    name = fields.Char(string='Name', trim=True, )
    module_id = fields.Many2one(comodel_name='prd.odoo_module',string="Odoo Module",help="") 
    prd_id = fields.Many2one(comodel_name='prd.document',string="Odoo Module",help="") 
    git_url = fields.Char(string='Git', trim=True, )
    file_type = fields.Selection(selection=[
        ('controllers','Controllers'),
        ('data','Data'),
        ('manifest','Manifest'),
        ('models','Models'),
        ('report','Report'),
        ('security','Security'),
        ('static','Static'),
        ('tests','Tests'),
        ('views','Views'),
        ('wizard','Wizard'),
        ('other','Other'),
            ],string='Type')
    content_type = fields.Selection(
        selection=[
            ('txt','Text'),
            ('py','Python'), 
            ('xml','XML'),
            ('js','Javascript'),
            ('json','Json'),
            ('scss','SCSS'),
            ('bin','Binary')
        ],
        compute='_compute_content_type',
        store=True,           
        inverse='_inverse_content_type',
        string='Content Type',
    )
    content = fields.Text(string='Content')
    content_js = fields.Text(string='Content',related="content",readonly=False)
    content_json = fields.Text(string='Content',related="content",readonly=False)
    content_py = fields.Text(string='Content',related="content",readonly=False)
    content_scss = fields.Text(string='Content',related="content",readonly=False)
    content_txt = fields.Text(string='Content',related="content",readonly=False)
    content_xml = fields.Text(string='Content',related="content",readonly=False)
    content_bin = fields.Binary()
    content_mime = fields.Char(string='Mime')

    @api.depends('name','content_mime')
    def _compute_content_type(self):
        for rec in self:
            if not rec.name:
                rec.content_type = 'txt'
                continue
            ext = rec.name.lower().split('.')[-1]
            if ext in dict(self._fields['content_type'].selection).keys():
                rec.content_type = ext
            elif rec.content_mime != 'text/plain':
                rec.content_type = 'bin'
            else:
                rec.content_type = 'txt'
    def _inverse_content_type(self):
        for rec in self:
            rec.content_type = rec.content_type

    def get_modules_files(self):
        for file in self:
            module = file.module_id
            _logger.warning(f"{module.technical_name}/{file.name}")
            f = module.repo_id.get_contents(f"{module.technical_name}/{file.name}",module.branch_id.name)
            if isinstance(f, ContentFile):
                file._create_update(f,module)
            else:
                raise UserError(f"{f}")
            
            
    @api.model
    def _create_update(self,file: ContentFile,module):
        _logger.warning(f"{file=} {module.name=}")
        ft = 'other'
        for file_type in dict(self._fields['file_type'].selection).keys():
            if file_type in file.path:
                ft = file_type
        mime = filetype.guess(base64.b64decode(file.content))
        content_mime = mime.mime if mime else ('image/svg+xml' if "<svg" in getattr(file, 'decoded_content', '').decode('utf-8') else 'text/plain')
        
        vals = {
            'name': '/'.join(file.path.split('/')[1:]),
            'module_id': module.id,
            'file_type': ft,
            'content': file.decoded_content.decode('utf-8') if content_mime == 'text/plain' else False,
            'content_bin': file.content if content_mime != 'text/plain' else False,
            'content_mime': content_mime,
            'git_url': file.download_url, 
        }
        _logger.warning(f"{vals=}")
        file_rec = self.search([
            ('module_id', '=', module.id), 
            ('name', '=', '/'.join(file.path.split('/')[1:]))
        ], limit=1)
        if file_rec:
            file_rec.write(vals)
        else:
            self.create(vals)

    def build_python_dir(self):
        init = {}
        for file_type in ['controllers','models','tests']:
            for file in self.search():
                pass
        

    def _build_module_structure(self, writer):
        data = []
        models_init = []
        controllers_init = []
        main_init = []

        # Process all functions
        for file in self.function_ids:
            if function.has_views and function.views_filename:
                writer.write_file("views/", function.views_filename, function.views_xml)
                data.append(f"views/{function.views_filename}")

            if function.has_models and function.models_filename:
                writer.write_file("models/", function.models_filename, function.models_src)
                split_filename = function.models_filename.split(".")[0]
                models_init.append(f"from . import {split_filename}")

            if function.has_data and function.data_filename:
                writer.write_file("data/", function.data_filename, function.data_xml)
                data.append(f"data/{function.data_filename}")

            if function.has_controllers and function.controllers_filename:
                writer.write_file("controllers/", function.controllers_filename, function.controllers_src)
                split_filename = function.controllers_filename.split(".")[0]
                controllers_init.append(f"from . import {split_filename}")

        # Create __init__.py files for models
        if models_init:
            content = "\n".join(models_init)
            writer.write_file("models/", "__init__.py", content)
            main_init.append("from . import models")

        # Create __init__.py files for controllers
        if controllers_init:
            content = "\n".join(controllers_init)
            writer.write_file("controllers/", "__init__.py", content)
            main_init.append("from . import controllers")

        # Create security files
        writer.write_file("security/", "ir.model.access.csv", self.create_ir_model_access())

        rec_rule_path = writer.write_file(
            "security/",
            f"{self.name}_record_rules.xml",
            self.create_record_rules()
        )
        # Extract relative path for manifest (remove module path prefix)
        rec_rule_relative = "/".join(rec_rule_path.split("/")[1:])
        data.append(rec_rule_relative)

        # Create main __init__.py
        main_init_content = "\n".join(main_init)
        writer.write_file("", "__init__.py", main_init_content)

        # Create manifest
        writer.write_file("", "__manifest__.py", self.create_manifest(data))

        return data


            
class ProductRequirementDocument(models.Model):
    _inherit = 'prd.document'

    # ~ files_count = fields.Integer(string="Total Requirements", related="module_id.files_count")
    # ~ file_ids = fields.One2many(related="module_id.file_ids")

    def action_files(self):
        action = {
          'type': 'ir.actions.act_window',
          'name': 'Files',
          'res_model': 'prd.odoo_module.file',
          'domain': [('module_id', '=', self.module_id.id)],
          'context': {'default_prd_id': self.id, 'default_module_id': self.module_id.id},
          'target': 'current',
        }
        if self.files_count > 0:
            action.update({'view_mode': 'list,form,kanban'})
        else:
            action.update({'view_mode': 'form,list,kanban'})
        return action
