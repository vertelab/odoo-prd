from github.ContentFile import ContentFile
from odoo import api, fields, models, _
from odoo.addons.prd_module.utils import TarFileWriter, SFTPFileWriter
from odoo.exceptions import UserError, ValidationError, AccessError
import base64
import filetype
import logging
import markdown
import ast
import re

_logger = logging.getLogger(__name__)


class OdooModule(models.Model):
    _inherit = "prd.odoo_module"

    # ~ function_ids = fields.Many2many(  # Inverse
    # ~ 'prd.function',
    # ~ string='Functions'
    # ~ )

    files_count = fields.Integer(
        string="Total Files", compute="_compute_file_counts", store=True
    )
    file_ids = fields.One2many("prd.odoo_module.file", "module_id", string="Files")
    branch_id = fields.Many2one(
        comodel_name="prd.odoo_branch", string="Branch", help=""
    )
    icon_file = fields.Binary(compute="_get_file_image")
    banner_file = fields.Binary(compute="_get_file_image")

    @api.depends("file_ids")
    def _get_file_image(self):
        for record in self:
            icon_file = record.file_ids.filtered(
                lambda f: f.name == "static/description/icon.png"
            )
            record.icon_file = icon_file.content_bin if icon_file else False
            banner_file = record.file_ids.filtered(
                lambda f: f.name == "static/description/banner.png"
            )
            record.banner_file = banner_file.content_bin if banner_file else False

    @api.depends("file_ids")
    def _compute_file_counts(self):
        for record in self:
            record.files_count = len(record.file_ids)

    def button_get_modules_files(self):
        self.ensure_one()
        if not all([self.repo_id, self.repo_id.owner, self.branch_id]):
            raise UserError(_("Missing repo, branch or owner"))
        files = self.repo_id.get_files(self.technical_name, self.branch_id.name)
        self.message_post(
            body=_(f"Get Module files {len(files)}"),
            subtype_xmlid="mail.mt_note",  # intern anteckning
        )
        for file in files:
            self.env["prd.odoo_module.file"]._create_update(file, self)
        return self.action_files()

    def action_files(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Files",
            "res_model": "prd.odoo_module.file",
            "domain": [("module_id", "=", self.id)],
            "context": {"default_module_id": self.id},
            "view_mode": "kanban,list,form",
            "target": "current",
        }

    def _build_module_structure(self, writer):
        self.ensure_one()

        if not self.file_ids:
            raise UserError(
                _("No files found on this module. Please fetch module files first.")
            )

        file_entries = []
        for file_rec in self.file_ids.filtered(lambda f: f.name):
            if file_rec.content_type == "bin" or (
                file_rec.content_mime and file_rec.content_mime != "text/plain"
            ):
                content = (
                    base64.b64decode(file_rec.content_bin)
                    if file_rec.content_bin
                    else b""
                )
            else:
                content = file_rec.content or ""

            file_entries.append((file_rec.name, content))

        self._write_module_files(writer, file_entries)


    def get_files(self):
        for m in self:
            self.env["prd.odoo_module.file"].get_modules_files(m)

    manifest_file_id = fields.Many2one(
        comodel_name="prd.odoo_module.file",
        string="Manifest",
        help="",
    )

    icon_image_file_id = fields.Many2one(
        comodel_name="prd.odoo_module.file",
        string="Icon",
        help="",
    )
    banner_image_file_id = fields.Many2one(
        comodel_name="prd.odoo_module.file",
        string="Banner",
        help="",
    )
    index_file_id = fields.Many2one(
        comodel_name="prd.odoo_module.file",
        string="Index",
        help="",
    )

    index_content = fields.Text(
        string="Index", related="index_file_id.content", readonly=False
    )


class OdooModuleFile(models.Model):
    _name = "prd.odoo_module.file"
    _description = "Files within a module"

    name = fields.Char(
        string="Name",
        trim=True,
    )
    module_id = fields.Many2one(
        comodel_name="prd.odoo_module", string="Odoo Module", help=""
    )
    # ~ prd_id = fields.Many2one(comodel_name='prd.document',string="PRD",help="")
    git_url = fields.Char(
        string="Git",
        trim=True,
    )
    file_type = fields.Selection(
        selection=[
            ("controllers", "Controllers"),
            ("data", "Data"),
            ("manifest", "Manifest"),
            ("models", "Models"),
            ("report", "Report"),
            ("security", "Security"),
            ("static", "Static"),
            ("tests", "Tests"),
            ("views", "Views"),
            ("wizard", "Wizard"),
            ("other", "Other"),
        ],
        string="Type",
    )
    content_type = fields.Selection(
        selection=[
            ("txt", "Text"),
            ("py", "Python"),
            ("xml", "XML"),
            ("js", "Javascript"),
            ("json", "Json"),
            ("scss", "SCSS"),
            ("svg", "SVG"),
            ("bin", "Binary"),
        ],
        compute="_compute_content_type",
        store=True,
        inverse="_inverse_content_type",
        string="Content Type",
    )
    content = fields.Text(string="Content")
    content_js = fields.Text(string="Content", related="content", readonly=False)
    content_json = fields.Text(string="Content", related="content", readonly=False)
    content_py = fields.Text(string="Content", related="content", readonly=False)
    content_scss = fields.Text(string="Content", related="content", readonly=False)
    content_txt = fields.Text(string="Content", related="content", readonly=False)
    content_xml = fields.Text(string="Content", related="content", readonly=False)
    content_bin = fields.Binary()
    content_mime = fields.Char(string="Mime")
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
    branch_name = fields.Char(
        string="module_id.branch_id.name", related="module_id.branch_id.name"
    )
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

    @api.depends("name", "content_mime")
    def _compute_content_type(self):
        for rec in self:
            if not rec.name:
                rec.content_type = "txt"
                continue
            ext = rec.name.lower().split(".")[-1]
            if ext in dict(self._fields["content_type"].selection).keys():
                rec.content_type = ext
            elif rec.content_mime != "text/plain":
                rec.content_type = "bin"
            else:
                rec.content_type = "txt"

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
            f = module.repo_id.get_contents(
                f"{module.technical_name}/{file.name}", module.branch_id.name
            )
            if isinstance(f, ContentFile):
                file._create_update(f, module)
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
    # ~ quest = self.env.ref('prd_module.build_views_bot_28')	__custom__.rpd
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
    def _create_update(self, file_object, module):
        """Create or update file record from git provider file object."""
        # Get the provider adapter to normalize the file
        adapter = module.repo_id._get_provider_adapter()
        file_info = adapter.normalize_file_object(file_object)

        _logger.info(f"Processing file: {file_info['name']} for module {module.name}")

        # Determine file type based on path
        ft = "other"
        pos = 1 if module.repo_id.owner != "odoo" else 2
        path_parts = file_info["path"].split("/")

        for file_type in dict(self._fields["file_type"].selection).keys():
            if len(path_parts) > pos and file_type in path_parts[pos]:
                ft = file_type
                break

        # Determine content type
        content_mime = file_info.get("mime_type", "text/plain")

        vals = {
            "name": file_info["relative_path"],
            "module_id": module.id,
            "file_type": ft,
            "content": (
                file_info["decoded_content"] if content_mime == "text/plain" else False
            ),
            "content_bin": (
                file_info["content"] if content_mime != "text/plain" else False
            ),
            "content_mime": content_mime,
            "git_url": file_info.get("download_url", ""),
        }

        _logger.debug(f"File values: {vals}")

        # Check if file already exists
        file_rec = self.search(
            [("module_id", "=", module.id), ("name", "=", file_info["relative_path"])],
            limit=1,
        )

        if file_rec:
            file_rec.write(vals)
            _logger.info(f"Updated existing file: {file_info['relative_path']}")
        else:
            self.create(vals)
            _logger.info(f"Created new file: {file_info['relative_path']}")

    def build_python_dir(self):
        init = {}
        for file_type in ["controllers", "models", "tests"]:
            for file in self.search():
                pass


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
    _inherit = "prd.document"

    manifest_file_id = fields.Many2one(
        comodel_name="prd.odoo_module.file",
        string="Manifest",
        help="",
    )

    icon_image_file_id = fields.Many2one(
        comodel_name="prd.odoo_module.file",
        string="Icon",
        help="",
    )
    banner_image_file_id = fields.Many2one(
        comodel_name="prd.odoo_module.file",
        string="Banner",
        help="",
    )
    index_file_id = fields.Many2one(
        comodel_name="prd.odoo_module.file",
        string="Index",
        help="",
    )

    branch_id = fields.Many2one(
        comodel_name="prd.odoo_branch",
        string="Branch",
        related="module_id.branch_id",
        help="",
    )
    module_id = fields.Many2one(
        comodel_name="prd.odoo_module", string="Module", help=""
    )

    index_content = fields.Text(
        string="Index", related="index_file_id.content", readonly=False
    )
    manifest_content = fields.Text(
        string="Manifest", related="manifest_file_id.content", readonly=False
    )

    model_access = fields.One2many(
        comodel_name="prd.model.access", 
        inverse_name="prd_id", 
        string="Model Access"
    )
    record_rule = fields.One2many(
        comodel_name="prd.rule", 
        inverse_name="prd_id", 
        string="Access Rules"
    )
    rule_groups = fields.One2many(
        comodel_name="prd.rule.groups", 
        inverse_name="prd_id", 
        string="Access Groups"
    )
    
    files_count = fields.Integer(string="Total Files", related="module_id.files_count")
    file_ids = fields.One2many(
        comodel_name="prd.odoo_module.file",
        related="module_id.file_ids",
        string="Files",
    )

    def action_files(self):
        action = {
            "type": "ir.actions.act_window",
            "name": "Files",
            "res_model": "prd.odoo_module.file",
            "domain": [("module_id", "=", self.module_id.id)],
            "context": {
                "default_prd_id": self.id,
                "default_module_id": self.module_id.id,
            },
            "target": "current",
        }
        if self.files_count > 0:
            action.update({"view_mode": "list,form,kanban"})
        else:
            action.update({"view_mode": "form,list,kanban"})
        return action


class AIQuest(models.Model):
    _inherit = "ai.quest"

    ai_type = fields.Selection(
        required=False,
        selection_add=[
            ("prd_module_mv_prompt", "Prd_module: Model/views prompt"),
            ("prd_module_views", "Prd_module: views"),
            ("prd_module_models", "Prd_module: models"),
            ("prd_module_data", "Prd_module: data"),
            ("prd_module_tests", "Prd_module: tests"),
            ("prd_module_doc", "Prd_module: documentation"),
            ("prd_module_report", "Prd_module: report"),
            ("prd_module_wizard", "Prd_module: wizard"),
        ],
        ondelete={  # YOUR ORIGINAL VALUES (from base model - add these!)
            "default": "set default",
            "ai-programmer": "cascade",
            "oos": "cascade",
            "ai-staff": "cascade",
            "prd_module_mv_prompt": "set null",
            "prd_module_views": "set null",
            "prd_module_models": "set null",
            "prd_module_data": "set null",
            "prd_module_tests": "set null",
            "prd_module_doc": "set null",
            "prd_module_report": "set null",
            "prd_module_wizard": "set null",
        },
    )
