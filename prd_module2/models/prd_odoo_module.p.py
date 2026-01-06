from github.ContentFile import ContentFile
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError
import base64
import filetype
import logging
import markdown
import ast
import re

_logger = logging.getLogger(__name__)



VIEW_FIELD_WIDGETS = """
| Widget | Description | Suitable Field Types | Odoo Versions |
| :-- | :-- | :-- | :-- |
| attachment_image | Displays attachments as images | binary | 16,17,18,19 |
| badge | Colored badges for status display | char,selection | 16,17,18,19 |
| badge_selection | Badge-style selection display | many2one,selection | 16,17,18,19 |
| badge_selection_with_filter | Badge with filtering capabilities | many2one | 17,18,19 |
| binary | File upload and download | binary | 14,15,16,17,18,19 |
| boolean | Standard checkbox | boolean | 14+ |
| boolean_favorite | Star icon for favorites | boolean | 16,17,18,19 |
| boolean_icon | Icon representation of boolean | boolean | 15+ |
| boolean_toggle | Toggle switch for boolean | boolean | 16,17,18,19 |
| char | Text input field | char | 14+ |
| color | Color display | integer,char | 14+ |
| color_picker | Color picker interface | char,integer | 16+ |
| contact_image | Contact profile image | binary,image | 17,18,19 |
| contact_statistics | Contact statistics display | many2one | 18,19 |
| copy_clipboard | Copy to clipboard button | char,text | 15+ |
| datetime | Date and time picker | datetime | 14+ |
| domain | Domain editor | char | 16+ |
| email | Email link with mailto | char | 14+ |
| field_selector | Field selection dropdown | char | 17+ |
| float | Decimal number input | float | 14+ |
| float_factor | Multiplier/percentage factor | float | 14+ |
| float_time | Time in decimal hours | float | 14+ |
| float_toggle | Toggle with float values | float | 16+ |
| gauge | Gauge chart visualization | float,integer | 15+ |
| google_slide_viewer | Google Slides viewer | char,url | 16+ |
| handle | Drag handle for reordering | integer | 14+ |
| html | Rich text/HTML editor | html | 14+ |
| iframe_wrapper | iFrame embedding wrapper | char | 16+ |
| image | Image display and upload | binary | 14+ |
| image_url | Image from external URL | char,url | 15+ |
| integer | Integer number input | integer | 14+ |
| ir_ui_view_ace | ACE editor for view XML | text | 16+ |
| journal_dashboard_graph | Journal dashboard graph | many2one | 15+ |
| json | JSON data editor | json | 17+ |
| json_checkboxes | JSON as checkbox list | json | 18,19 |
| kanban_color_picker | Kanban color picker | integer | 18,19 |
| label_selection | Selection with labels | selection | 15+ |
| many2many_binary | Many2many file attachments | many2many(binary) | 15+ |
| many2many_checkboxes | Many2many as checkboxes | many2many | 16+ |
| many2many_tags | Tag-style many2many | many2many | 14+ |
| many2many_tags_avatar | Tags with user avatars | many2many | 17+ |
| many2one | Standard many2one dropdown | many2one | 14+ |
| many2one_avatar | Many2one with avatar | many2one | 16+ |
| many2one_barcode | Many2one with barcode scan | many2one | 16+ |
| many2one_reference | Dynamic model reference | reference | 15+ |
| many2one_reference_integer | Integer-based reference | reference | 16+ |
| monetary | Currency amount display | monetary | 14+ |
| pdf_viewer | PDF document viewer | binary | 15+ |
| percent_pie | Percentage pie chart | float | 15+ |
| percentage | Percentage input | float | 14+ |
| phone | Phone link with tel protocol | char | 14+ |
| priority | Priority stars rating | selection | 14+ |
| progress_bar | Progress bar visualization | float,integer | 14+ |
| properties | Dynamic properties editor | properties | 18,19 |
| radio | Radio button selection | selection | 14+ |
| reference | Reference field to any model | reference | 14+ |
| remaining_days | Days remaining counter | integer,float | 16+ |
| selection | Dropdown selection | selection | 14+ |
| signature | Signature pad drawing | binary | 15+ |
| stat_info | Statistical information display | char,many2one | 16+ |
| state_selection | State-based selection | selection | 16+ |
| statusbar | Horizontal status bar | selection | 14+ |
| text | Multi-line text area | text | 14+ |
| timezone_mismatch | Timezone mismatch warning | datetime | 17+ |
| url | Clickable URL link | char | 14+ |
| x2many | Embedded relational lists | one2many,many2many | 14+ |
"""


class OdooModule(models.Model):
    _inherit = 'prd.odoo_module'

    # ~ function_ids = fields.Many2many(  # Inverse
        # ~ 'prd.function',
        # ~ string='Functions'
    # ~ )


    files_count = fields.Integer(string="Total Files", compute='_compute_file_counts',store=True)
    file_ids = fields.One2many('prd.odoo_module.file', 'module_id', string="Files")
    branch_id = fields.Many2one(comodel_name='prd.odoo_branch',string="Branch",help="")
    icon_file = fields.Binary(compute="_get_file_image")
    banner_file = fields.Binary(compute="_get_file_image")

    
    @api.depends('file_ids')
    def _get_file_image(self):
        for record in self:
            icon_file = record.file_ids.filtered(lambda f: f.name == 'static/description/icon.png')
            record.icon_file = icon_file.content_bin if icon_file else False
            banner_file = record.file_ids.filtered(lambda f: f.name == 'static/description/banner.png')
            record.banner_file = banner_file.content_bin if banner_file else False
    
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
            body=_(f"Get Module files {len(files)}"),
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


    manifest_file_id = fields.Many2one(comodel_name='prd.odoo_module.file',
                    string="Manifest",
                    help="", 
                    )

    icon_image_file_id = fields.Many2one(comodel_name='prd.odoo_module.file',
                    string="Icon",
                    help="", 
 
                    ) 
    banner_image_file_id = fields.Many2one(comodel_name='prd.odoo_module.file',
                    string="Banner",
                    help="", 
                    ) 
    index_file_id = fields.Many2one(comodel_name='prd.odoo_module.file',
                    string="Index",
                    help="", 
                    ) 

    index_content = fields.Text(string='Index',related="index_file_id.content",readonly=False)

class OdooModuleFile(models.Model):
    _name = 'prd.odoo_module.file'
    _description = 'Files within a module'
    
    name = fields.Char(string='Name', trim=True, )
    module_id = fields.Many2one(comodel_name='prd.odoo_module',string="Odoo Module",help="") 
    # ~ prd_id = fields.Many2one(comodel_name='prd.document',string="PRD",help="") 
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
            ('svg','SVG'),
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
    # ~ odoo_view_ids = fields.Many2many(
        # ~ comodel_name='prd.odoo_view_type',
        # ~ string='View Types',
        # ~ help=""
    # ~ )
    # ~ related_model = fields.Many2one(comodel_name='prd.odoo_module.file',string="Related Model",help="",domain="[('module_id','=',module_id),('file_type','=','models')]") 
    # ~ related_views_ids = fields.Many2one(comodel_name='prd.odoo_module.file',string="Related Model",help="",compute="_related_views_ids") 
    # ~ views_prompt = fields.Text(string='Prompt')
    # ~ views_replace = fields.Boolean(string='Replace',help="replace code or add to the bottom")
    # ~ views_fields_widgets = fields.Text(string='Fields Widgets',default=VIEW_FIELD_WIDGETS)
    # ~ content_related_model =  fields.Text(string='Content',compute="_compute_related_model",inverse="_inverse_related_model",store=True)
    # ~ views_instructions = fields.Text(string='Instructions for choosen views',compute="_views_instructions")
    branch_name = fields.Char(string='module_id.branch_id.name',related="module_id.branch_id.name")
    # ~ related_view_file_ids = fields.Many2many(
        # ~ comodel_name='prd.odoo_module.file',
        # ~ relation='prd_odoo_module_file_related_views_rel',  # Unik relationstabell
        # ~ column1='file_id',
        # ~ column2='related_view_id',
        # ~ string='Related View Files',
        # ~ help='Välj relaterade vy-filer',
        # ~ domain="[('file_type', '=', 'views')]" 
    # ~ )
    # ~ selectable_related_views = fields.Many2many(
        # ~ 'prd.odoo_module.file',
        # ~ compute='_compute_selectable_related_views',
        # ~ string='Selectable Related Views'
    # ~ )

    # ~ @api.depends('module_id','module_id.dependency_ids')
    # ~ def _compute_selectable_related_views(self):
        # ~ for rec in self:
            # ~ dep_modules = rec.module_id.dependency_ids.mapped('dep_module_id')
            # ~ view_ids = (dep_modules.file_ids).filtered(
                # ~ lambda f: f.file_type == 'views'
            # ~ ).ids
            # ~ rec.selectable_related_views = [(6, 0, view_ids)]



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
            
    # ~ @api.depends('related_model')
    # ~ def _compute_related_model(self):
        # ~ for rec in self:
            # ~ if rec.related_model:
                # ~ rec.content_related_model = rec.related_model.content
    # ~ def _inverse_related_model(self):
        # ~ for rec in self:
            # ~ rec.related_model.content = rec.content_related_model

    def get_modules_files(self):
        for file in self:
            module = file.module_id
            _logger.warning(f"{module.technical_name}/{file.name}")
            f = module.repo_id.get_contents(f"{module.technical_name}/{file.name}",module.branch_id.name)
            if isinstance(f, ContentFile):
                file._create_update(f,module)
            else:
                raise UserError(f"{f}")
                
                
    # ~ def _related_views_ids(self):
        # ~ view_ids = self.mapped('dependency_ids.module_id.file_ids').filtered(
                                            # ~ lambda f: f.file_type == 'views'
                                    # ~ ).ids
        # ~ for rec in self:
            # ~ rec.related_views_ids = [(6, 0, view_ids)]
                
    # ~ def _views_instructions(self):
        
        
        # ~ vi = "### VIEWS INSTRUCTIONS\n" + '\n'.join([
                # ~ f"View type {v.name}: special instructions for this view {v.prompt}" 
                # ~ for v in self.odoo_view_ids
            # ~ ])        

        # ~ views_dependent = ""
        # ~ models = self.identify_all_odoo_models()
        # ~ for model_info in models.get('_inherit', []):
            # ~ if len(self.related_view_file_ids)>0:
                # ~ views_dependent = f"""
# ~ ### Views from dependent modules

# ~ {'\n'.join(self.related_view_file_ids.mapped('content'))}

# ~ * When inheriting a view, set the record id equal to the last part of the inherit_id ref, without the module name.
         # ~ For example, if <field name="inherit_id" ref="project.edit_project" /> then write <record id="edit_project" model="ir.ui.view">.
# ~ * Do not include the module name in the new view’s id.
# ~ * In the name field, add a significant part from the module name {self.module_id.technical_name}

# ~ """
            # ~ fields = '\n'.join(model_info.get('fields', []))
            # ~ vi += f"""\n\n### INHERITED MODELS - USE INHERITED VIEWS
    # ~ - **ALWAYS** inherit from standard views with correct names

    # ~ #### MODEL: {model_info['model_name']} (inherit)
    # ~ {model_info.get('description', '')}
    # ~ Fields in the model
    # ~ {fields}

    # ~ use these fields in these views: 
    # ~ {','.join([v.name for v in self.odoo_view_ids])}
    
    # ~ {views_dependent}

    # ~ Use appropriate widgets"""
        
        # ~ for model_info in models.get('_name', []):
            # ~ fields = '\n'.join([f"{f.name}: {f.type}" for f in model_info.get('fields', [])])
            # ~ vi += f"""\n### NEW MODELS - BUILD NEW VIEWS, RECORDS, ACTIONS AND MENU

    # ~ #### MODEL: {model_info['model_name']} 
    # ~ {model_info.get('description', '')}
    # ~ Fields in the model
    # ~ {fields}

    # ~ Use appropriate widgets"""
            
            # ~ if model_info.get('has_chatter') and self.odoo_view_ids.filtered(lambda f: f.code == 'form'):
                # ~ vi += "\nAdd chatter to the form view\n"
        
        # ~ self.views_instructions = vi

    
    

    # ~ def views_prompt_do(self):
        # ~ quest = self.env.ref('prd_module2.build_views_bot_28')	__custom__.rpd
        # ~ quest = self.env.ref('__custom__.rpd')	
        # ~ result = quest.run(record=self)
        # ~ raise UserError(f"{self.views_prompt=} {self=} {result=}")
        # ~ if result:
            # ~ ai_messages = quest._get_last_ai_message(result.get('result', {}).get('messages', False))
            # ~ if self.views_replace:
                # ~ self.content =  ai_messages.content
            # ~ else:
                # ~ self.content +=  ai_messages.content
        # ~ else:
            # ~ raise UserError(_(f"OBS: An error occurred, you should contact administrator to look into the quest {result=}"))

        
        
        
    @api.model
    def _create_update(self,file: ContentFile,module):
        _logger.warning(f"{file=} {module.name=}")
        ft = 'other'
        pos = 1 if module.repo_id.owner != 'odoo' else 2
        for file_type in dict(self._fields['file_type'].selection).keys():
            if file_type in path_list[pos] if len(path_list := file.path.split('/')) > pos else path_list[pos-1]:
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

    # ~ def identify_all_odoo_models(self) -> dict:
        # ~ """
        # ~ Finds all Odoo models referenced or defined in the code.
        
        # ~ Args:
            # ~ code (str): Python source code containing Odoo model definitions
            
        # ~ Returns:
            # ~ dict: Dictionary with model information:
                # ~ {
                    # ~ '_name': [list_of_new_models],
                    # ~ '_inherit': [list_of_inherited_models]
                # ~ }
                # ~ Each model contains:
                # ~ - 'model_name': str (technical model name)
                # ~ - 'has_chatter': bool
                # ~ - 'description': str | None (class docstring)
        # ~ """
        
        # ~ def has_mail_thread(code: str, model_name: str) -> bool:
            # ~ """
            # ~ Detects if model has chatter support via mail.thread or mail.activity.mixin inheritance.
            # ~ """
            # ~ # Direct _inherit = 'mail.thread' or 'mail.activity.mixin'
            # ~ direct_inherit = re.search(
                # ~ rf"_inherit\s*=\s*['\"]mail\.(thread|activity\.mixin)['\"]", 
                # ~ code
            # ~ )
            # ~ if direct_inherit:
                # ~ return True
            
            # ~ # Multiple inheritance in class definition
            # ~ class_pattern = rf'class\s+\w+\s*\([^)]*[\'"]{re.escape(model_name)}[\'"]'
            # ~ class_match = re.search(class_pattern, code, re.MULTILINE | re.DOTALL)
            
            # ~ if class_match:
                # ~ # Look for mail.thread or mail.activity.mixin in inheritance tuple
                # ~ inherit_pattern = r"['\"]mail\.(thread|activity\.mixin)['\"]"
                # ~ if re.search(inherit_pattern, class_match.group(0)):
                    # ~ return True
            
            # ~ # Check _inherit list/tuple containing mail.thread
            # ~ inherit_list_pattern = r"_inherit\s*=\s*\[(?:.*?['\"]mail\.(thread|activity\.mixin)['\"].*?)*\]"
            # ~ if re.search(inherit_list_pattern, code):
                # ~ return True
            
            # ~ return False

        # ~ def extract_fields(code: str, model_name: str) -> list[dict]:
            # ~ fields = []
            # ~ fields_re = re.findall(r'^(\s*)([a-z_][a-z0-9_]*)?\s*=\s*fields\.([A-Za-z_][a-zA-Z0-9_]*)', code, re.MULTILINE)
            # ~ for tab,name,ftype in fields_re:
                # ~ fields.append(f"{name}: {ftype}")
            # ~ return fields
        
        # ~ models = {'_name': [], '_inherit': []}
        # ~ code = self.related_model.content
        
        # ~ name_matches = re.findall(r"_name\s*=\s*['\"]([^'\"]+)['\"]", code)
        # ~ inherit_matches = re.findall(r"_inherit\s*=\s*['\"]([^'\"]+)['\"]", code)
                
        # ~ for model in list(set(name_matches + inherit_matches)):
            # ~ docstring_match = re.search(
                # ~ rf'class\s+\w+\s*\([^)]*[\'"]{re.escape(model)}[\'"]\s*:\s*"""\s*(.*?)\s*"""',
                # ~ code, re.DOTALL | re.MULTILINE
            # ~ )
            # ~ models['_name' if model in name_matches else '_inherit'].append(
                        # ~ {
                            # ~ 'model_name': model,
                            # ~ 'description': docstring_match.group(1).strip() if docstring_match else None,
                            # ~ 'fields': extract_fields(code, model),
                            # ~ 'has_chatter': has_mail_thread(code, model),
                        # ~ }
                    # ~ )
        
        # ~ return models
            
class ProductRequirementDocument(models.Model):
    _inherit = 'prd.document'


    manifest_file_id = fields.Many2one(comodel_name='prd.odoo_module.file',
                    string="Manifest",
                    help="", 
                    )

    icon_image_file_id = fields.Many2one(comodel_name='prd.odoo_module.file',
                    string="Icon",
                    help="", 

                    ) 
    banner_image_file_id = fields.Many2one(comodel_name='prd.odoo_module.file',
                    string="Banner",
                    help="", 
                    ) 
    index_file_id = fields.Many2one(comodel_name='prd.odoo_module.file',
                    string="Index",
                    help="", 
                    ) 

    branch_id = fields.Many2one(comodel_name='prd.odoo_branch',string='Branch',related="module_id.branch_id", help="")
    module_id = fields.Many2one(comodel_name='prd.odoo_module', string="Module", help="")

    index_content = fields.Text(string='Index',related="index_file_id.content",readonly=False)
    manifest_content = fields.Text(string='Manifest',related="manifest_file_id.content",readonly=False)
    
    model_access = fields.Many2many(comodel_name='prd.model.access',string='Model Access',help="") # relation|column1|column2
    record_rule = fields.Many2many(comodel_name='prd.rule',string='Access Rules',help="") # relation|column1|column2
    rule_groups = fields.Many2many(comodel_name='prd.rule.groups',string='Access Group',help="") # relation|column1|column2
    files_count = fields.Integer(string="Total Files", related="module_id.files_count")
    file_ids = fields.One2many(comodel_name='prd.odoo_module.file', related="module_id.file_ids", string="Files")

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
    

class AIQuest(models.Model):
    _inherit = "ai.quest"

    ai_type = fields.Selection(required=False,
        selection_add=[
            ('prd_module_mv_prompt', 'Prd_module: Model/views prompt'), 
            ('prd_module_views', 'Prd_module: views'), 
            ('prd_module_models', 'Prd_module: models'), 
            ('prd_module_data', 'Prd_module: data'), 
            ('prd_module_tests', 'Prd_module: tests'), 
            ('prd_module_doc', 'Prd_module: documentation'), 
            ('prd_module_report', 'Prd_module: report'), 
            ('prd_module_wizard', 'Prd_module: wizard'), 
        ],
        ondelete={            # YOUR ORIGINAL VALUES (from base model - add these!)
            'default': 'set default',
            'ai-programmer': 'cascade',
            'oos': 'cascade', 
            'ai-staff': 'cascade',
            'prd_module_mv_prompt': 'set null',
            'prd_module_views': 'set null',
            'prd_module_models': 'set null', 
            'prd_module_data': 'set null',
            'prd_module_tests': 'set null',
            'prd_module_doc': 'set null',
            'prd_module_report': 'set null',
            'prd_module_wizard': 'set null',
        }
    )
