from github.ContentFile import ContentFile
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError
import logging
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


class PrdFunction(models.Model):
    _inherit = "prd.function"

    ## Model/View
    prompt_model = fields.Text(
        string="Prompt (model)", placeholder="e.g. Promt for python code"
    )
    # ~ library_ids = fields.Many2many(comodel_name='prd.odoo_library',string='Libraries',help="")
    prompt_tests = fields.Text(string="Prompt (tests)")
    prompt_data = fields.Text(string="Prompt (tests)")
    model_file_id = fields.Many2one(
        comodel_name="prd.odoo_module.file",
        string="Model",
        help="",
    )
    tests_file_id = fields.Many2one(
        comodel_name="prd.odoo_module.file",
        string="Tests",
        help="",
    )
    data_file_id = fields.Many2one(
        comodel_name="prd.odoo_module.file",
        string="Data",
        help="",
    )
    content_model = fields.Text(
        string="Model", related="model_file_id.content", readonly=False
    )
    content_tests = fields.Text(
        string="Test", related="tests_file_id.content", readonly=False
    )
    content_data = fields.Text(
        string="Test", related="data_file_id.content", readonly=False
    )
    # ~ dep_ids = fields.Many2many(comodel_name='prd.odoo_module',string='Dependencies',)
    dependency_ids = fields.Many2many(
        comodel_name="prd.odoo_module",
        string="Dependencies",
    )
    # ~ dependency_ids = fields.Many2many(
    # ~ comodel_name='prd.odoo_module',
    # ~ relation='prd_odoo_module_function_dependenciesxxx_rel',
    # ~ column1='func_id',      # func_id pekar på prd.function.id
    # ~ column2='module_id'     # module_id pekar på prd.odoo_module.id
    # ~ )
    # ~ app_category_id = fields.Many2one('ir.module.category', string="Category")
    application = fields.Boolean(string="Application")
    # ~ auto_install = fields.Boolean('Automatic Installation',
    # ~ help='An auto-installable module is automatically installed by the '
    # ~ 'system when all its dependencies are satisfied. '
    # ~ 'If the module has no dependency, it is always installed.')
    # ~ author = fields.Char("Author")

    # ~ contributors = fields.Text('Contributors')
    # ~ licence_id = fields.Many2one(comodel_name='prd.odoo_licence', string="Licence", help="")
    # ~ maintainer = fields.Char('Maintainer')
    repo_id = fields.Many2one(
        comodel_name="prd.odoo_repo",
        related="module_id.repo_id",
        string="Repo",
        help="",
    )
    # ~ rule_ids = fields.One2many(comodel_name="prd.rule", inverse_name="prd_id")
    summary = fields.Char(string="Summary")
    technical_name = fields.Char(string="Technical Name")
    website = fields.Char(string="Website")
    description_html = fields.Text(string="_")

    prd_information = fields.Text(
        string="PRD Information", compute="_compute_prd_information"
    )

    @api.depends("dependency_ids.module_id")
    def _compute_prd_information(self):
        for rec in self:
            rec.prd_information = f"""#### PRD information for {rec.prd_id.name}
{rec.prd_id.description}
#### PRD Goals
{rec.prd_id.goals}
#### PRD Success Criteria 
{rec.prd_id.success_criteria}
#### PRD risks
{rec.prd_id.risks}
"""

    ## Wizard

    ## Report

    ## Security
    branch_name = fields.Char(string="Branch", related="prd_id.branch_id.name")
    replace_content = fields.Boolean(
        string="Replace", help="replace code or add to the bottom"
    )

    def model_prompt_do(self):
        quest = self.env["ai.quest"].get_ai_type("prd_module_model")
        result = quest.run(record=self)
        raise UserError(f"{self.views_prompt=} {self=} {result=}")
        if result:
            ai_messages = quest._get_last_ai_message(
                result.get("result", {}).get("messages", False)
            )
            if self.views_replace:
                self.content = ai_messages.content
            else:
                self.content += ai_messages.content
        else:
            raise UserError(
                _(
                    f"OBS: An error occurred, you should contact administrator to look into the quest {result=}"
                )
            )
            # ~ raise UserError(f"{ai_messages=}")
            # ~ if not ai_messages:
            # ~ raise UserError(_("OBS: An error occurred, you should contact administrator to look into the quest"))

            # ~ if ai_quest.debug:
            # ~ answer = markdown.markdown(ai_messages.content)
            # ~ else:
            # ~ answer = re.sub(
            # ~ r'<think>.*?</think>', '', markdown.markdown(ai_messages.content), flags=re.DOTALL)

            # ~ return answer
        # ~ raise UserError(_("OBS: An error occurred, you should contact administrator to look into the quest"))

        # ~ pass

    def create_mv_prompt(self):
        quest = self.env["ai.quest"].get_ai_type("prd_module_mv_prompt")
        # ~ for f in self._fields.keys():
        # ~ try:
        # ~ foo = self.read([f])[0]
        # ~ _logger.error(f"{f=}")
        # ~ except Exception as e:
        # ~ _logger.error(f"{f=} {e}")
        result = quest.run(record=self)
        if result:
            ai_messages = quest._get_last_ai_message(
                result.get("result", {}).get("messages", False)
            )
            if self.views_replace:
                self.content = ai_messages.content
            else:
                self.content += ai_messages.content
        else:
            raise UserError(
                _(
                    f"OBS: An error occurred, you should contact administrator to look into the quest {result=}"
                )
            )

    def create_wizard_prompt(self):
        # ~ quest = self.env.ref('prd_module2.build_views_bot_28')	__custom__.rpd
        quest = self.env.ref("__custom__.rpd")
        result = quest.run(record=self)
        if result:
            ai_messages = quest._get_last_ai_message(
                result.get("result", {}).get("messages", False)
            )
            if self.views_replace:
                self.content = ai_messages.content
            else:
                self.content += ai_messages.content
        else:
            raise UserError(
                _(
                    f"OBS: An error occurred, you should contact administrator to look into the quest {result=}"
                )
            )

    def create_report_prompt(self):
        # ~ quest = self.env.ref('prd_module2.build_views_bot_28')	__custom__.rpd
        quest = self.env.ref("__custom__.rpd")
        result = quest.run(record=self)
        if result:
            ai_messages = quest._get_last_ai_message(
                result.get("result", {}).get("messages", False)
            )
            if self.views_replace:
                self.content = ai_messages.content
            else:
                self.content += ai_messages.content
        else:
            raise UserError(
                _(
                    f"OBS: An error occurred, you should contact administrator to look into the quest {result=}"
                )
            )

    def data_prompt_do(self):
        result = self.env["ai.quest"].get_ai_type("prd_module_data").run(record=self)
        if result:
            ai_messages = quest._get_last_ai_message(
                result.get("result", {}).get("messages", False)
            )
            if self.views_replace:
                self.content = ai_messages.content
            else:
                self.content += ai_messages.content
        else:
            raise UserError(
                _(
                    f"OBS: An error occurred, you should contact administrator to look into the quest {result=}"
                )
            )
            # ~ raise UserError(f"{ai_messages=}")
            # ~ if not ai_messages:
            # ~ raise UserError(_("OBS: An error occurred, you should contact administrator to look into the quest"))

            # ~ if ai_quest.debug:
            # ~ answer = markdown.markdown(ai_messages.content)
            # ~ else:
            # ~ answer = re.sub(
            # ~ r'<think>.*?</think>', '', markdown.markdown(ai_messages.content), flags=re.DOTALL)

            # ~ return answer
        # ~ raise UserError(_("OBS: An error occurred, you should contact administrator to look into the quest"))

    def tests_prompt_do(self):
        result = self.env["ai.quest"].get_ai_type("prd_module_tests").run(record=self)
        # ~ raise UserError(f"{self.views_prompt=} {self=} {result=}")
        if result:
            ai_messages = quest._get_last_ai_message(
                result.get("result", {}).get("messages", False)
            )
            if self.views_replace:
                self.content = ai_messages.content
            else:
                self.content += ai_messages.content
        else:
            raise UserError(
                _(
                    f"OBS: An error occurred, you should contact administrator to look into the quest {result=}"
                )
            )
            # ~ raise UserError(f"{ai_messages=}")
            # ~ if not ai_messages:
            # ~ raise UserError(_("OBS: An error occurred, you should contact administrator to look into the quest"))

            # ~ if ai_quest.debug:
            # ~ answer = markdown.markdown(ai_messages.content)
            # ~ else:
            # ~ answer = re.sub(
            # ~ r'<think>.*?</think>', '', markdown.markdown(ai_messages.content), flags=re.DOTALL)

            # ~ return answer
        # ~ raise UserError(_("OBS: An error occurred, you should contact administrator to look into the quest"))

    ######
    #
    #   Views
    #
    ######
    prompt_views = fields.Text(string="Prompt (views)")
    content_views = fields.Text(
        string="Views", related="views_file_id.content", readonly=False
    )
    views_file_id = fields.Many2one(
        comodel_name="prd.odoo_module.file",
        string="Views",
        help="",
    )
    views_replace = fields.Boolean(
        string="Replace", help="replace code or add to the bottom"
    )

    views_file_related_ids = fields.Many2many(
        comodel_name="prd.odoo_module.file",
        relation="prd_odoo_module_views_file_related_rel",
        column1="file_id",
        column2="related_view_id",
        string="Related View Files",
        help="Choose related view files",
        domain="[('file_type', '=', 'views')]",
    )
    selectable_related_views = fields.Many2many(
        "prd.odoo_module.file",
        compute="_compute_selectable_related_views",
        string="Selectable Related Views",
    )

    @api.depends("dependency_ids.module_id")
    def _compute_selectable_related_views(self):
        for rec in self:
            file_records = self.env["prd.odoo_module.file"]
            # SÄKERT: Kontrollera att module_id har file_ids
            # ~ _logger.error(f"filer :::: {rec.dependency_ids.mapped('module_id.file_ids').filtered(lambda f: f.file_type in ['views', 'wizards'])}")

            for dep in rec.dependency_ids:
                module = dep.module_id  # eller dep.dep_module_id etc.
                _logger.error(f"filer :::: {module._name=}  {module.name=}")
                if module and hasattr(module, "file_ids") and module.file_ids:
                    _logger.error(f"filer :::: {module.file_ids}")
                    file_records |= module.file_ids.filtered(
                        lambda f: f.file_type in ["views", "wizards"]
                    )
                else:  # this should not be necessery
                    prd_module = self.env["prd.odoo_module"].search(
                        [("technical_name", "=", module.name)]
                    )
                    file_records |= prd_module.file_ids.filtered(
                        lambda f: f.file_type in ["views", "wizards"]
                    )
            rec.selectable_related_views = file_records

    # ~ @api.depends('dependency_ids')
    # ~ def _compute_selectable_related_views(self):
    # ~ for rec in self:
    # ~ dep_modules = rec.dependency_ids.mapped('module_id.file_ids').filtered(
    # ~ lambda f: f.file_type == 'views'
    # ~ ).ids
    # ~ rec.selectable_related_views = [(6, 0, dep_modules)]

    views_fields_widgets = fields.Text(
        string="Fields Widgets", default=VIEW_FIELD_WIDGETS
    )
    views_instructions = fields.Text(
        string="Instructions for choosen views", compute="_views_instructions"
    )

    def _views_file_related_ids(self):
        view_ids = (
            self.mapped("dep_ids.module_id.file_ids")
            .filtered(lambda f: f.file_type == "views")
            .ids
        )
        for rec in self:
            rec.views_file_related_ids = [(6, 0, view_ids)]

    def _views_instructions(self):
        vi = "### VIEWS INSTRUCTIONS\n" + "\n".join(
            [
                f"View type {v.name}: special instructions for this view {v.prompt}"
                for v in self.odoo_view_ids
            ]
        )
        views_dependent = ""
        models = self.identify_all_odoo_models()
        for model_info in models.get("_inherit", []):
            _logger.error(f"Has _inherit")
            if len(self.views_file_related_ids) > 0:
                views_dependent = f"""
### Views from dependent modules

{'\n'.join(self.views_file_related_ids.mapped('content'))}

* When inheriting a view, set the record id equal to the last part of the inherit_id ref, without the module name.
         For example, if <field name="inherit_id" ref="project.edit_project" /> then write <record id="edit_project" model="ir.ui.view">.
* Do not include the module name in the new view’s id.
* In the name field, add a significant part from the module name {self.module_id.technical_name}

"""
            fields = "\n".join(model_info.get("fields", []))
            vi += f"""\n\n### INHERITED MODELS - USE INHERITED VIEWS
    - **ALWAYS** inherit from standard views with correct names

    #### MODEL: {model_info['model_name']} (inherit)
    {model_info.get('description', '')}
    Fields in the model
    {fields}

    use these fields in these views: 
    {','.join([v.name for v in self.odoo_view_ids])}
    
    {views_dependent}

    Use appropriate widgets"""

        for model_info in models.get("_name", []):
            _logger.error(f"Has _name")
            fields = "\n".join(
                [f"{f.name}: {f.type}" for f in model_info.get("fields", [])]
            )
            vi += f"""\n### NEW MODELS - BUILD NEW VIEWS, RECORDS, ACTIONS AND MENU

    #### MODEL: {model_info['model_name']} 
    {model_info.get('description', '')}
    Fields in the model
    {fields}

    Use appropriate widgets"""

            if model_info.get("has_chatter") and self.odoo_view_ids.filtered(
                lambda f: f.code == "form"
            ):
                vi += "\nAdd chatter to the form view\n"

        self.views_instructions = vi

    def views_prompt_do(self):
        # ~ quest = self.env.ref('prd_module2.build_views_bot_28')	__custom__.rpd
        result = self.env["ai.quest"].get_ai_type("prd_module_views").run(record=self)
        if result:
            ai_messages = quest._get_last_ai_message(
                result.get("result", {}).get("messages", False)
            )
            if self.views_replace:
                self.content = ai_messages.content
            else:
                self.content += ai_messages.content
        else:
            raise UserError(
                _(
                    f"OBS: An error occurred, you should contact administrator to look into the quest {result=}"
                )
            )
            # ~ raise UserError(f"{ai_messages=}")
            # ~ if not ai_messages:
            # ~ raise UserError(_("OBS: An error occurred, you should contact administrator to look into the quest"))

            # ~ if ai_quest.debug:
            # ~ answer = markdown.markdown(ai_messages.content)
            # ~ else:
            # ~ answer = re.sub(
            # ~ r'<think>.*?</think>', '', markdown.markdown(ai_messages.content), flags=re.DOTALL)

            # ~ return answer
        # ~ raise UserError(_("OBS: An error occurred, you should contact administrator to look into the quest"))

        # ~ pass

    def identify_all_odoo_models(self) -> dict:
        """
        Finds all Odoo models referenced or defined in the code.

        Args:
            code (str): Python source code containing Odoo model definitions

        Returns:
            dict: Dictionary with model information:
                {
                    '_name': [list_of_new_models],
                    '_inherit': [list_of_inherited_models]
                }
                Each model contains:
                - 'model_name': str (technical model name)
                - 'has_chatter': bool
                - 'description': str | None (class docstring)
        """

        def has_mail_thread(code: str, model_name: str) -> bool:
            """
            Detects if model has chatter support via mail.thread or mail.activity.mixin inheritance.
            """
            # Direct _inherit = 'mail.thread' or 'mail.activity.mixin'
            direct_inherit = re.search(
                rf"_inherit\s*=\s*['\"]mail\.(thread|activity\.mixin)['\"]", code
            )
            if direct_inherit:
                return True

            # Multiple inheritance in class definition
            class_pattern = rf'class\s+\w+\s*\([^)]*[\'"]{re.escape(model_name)}[\'"]'
            class_match = re.search(class_pattern, code, re.MULTILINE | re.DOTALL)

            if class_match:
                # Look for mail.thread or mail.activity.mixin in inheritance tuple
                inherit_pattern = r"['\"]mail\.(thread|activity\.mixin)['\"]"
                if re.search(inherit_pattern, class_match.group(0)):
                    return True

            # Check _inherit list/tuple containing mail.thread
            inherit_list_pattern = r"_inherit\s*=\s*\[(?:.*?['\"]mail\.(thread|activity\.mixin)['\"].*?)*\]"
            if re.search(inherit_list_pattern, code):
                return True

            return False

        def extract_fields(code: str, model_name: str) -> list[dict]:
            fields = []
            fields_re = re.findall(
                r"^(\s*)([a-z_][a-z0-9_]*)?\s*=\s*fields\.([A-Za-z_][a-zA-Z0-9_]*)",
                code,
                re.MULTILINE,
            )
            for tab, name, ftype in fields_re:
                fields.append(f"{name}: {ftype}")
            return fields

        models = {"_name": [], "_inherit": []}
        if not self.model_file_id:
            raise UserError(f"Missing model file")
        code = self.model_file_id.content

        name_matches = re.findall(r"_name\s*=\s*['\"]([^'\"]+)['\"]", code)
        inherit_matches = re.findall(r"_inherit\s*=\s*['\"]([^'\"]+)['\"]", code)

        for model in list(set(name_matches + inherit_matches)):
            docstring_match = re.search(
                rf'class\s+\w+\s*\([^)]*[\'"]{re.escape(model)}[\'"]\s*:\s*"""\s*(.*?)\s*"""',
                code,
                re.DOTALL | re.MULTILINE,
            )
            models["_name" if model in name_matches else "_inherit"].append(
                {
                    "model_name": model,
                    "description": (
                        docstring_match.group(1).strip() if docstring_match else None
                    ),
                    "fields": extract_fields(code, model),
                    "has_chatter": has_mail_thread(code, model),
                }
            )

        return models
