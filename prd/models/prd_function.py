from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError
import logging
from random import randint
from odoo.addons.base.models.avatar_mixin import get_hsl_from_seed
from secrets import choice
import base64
from odoo.tools.misc import topological_sort, get_flag

_logger = logging.getLogger(__name__)

xfunction_icon = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="#875a7b">
  <circle cx="32" cy="32" r="30" fill="#875a7b" />
  <g fill="#ffffff">
    <!-- Central circle -->
    <circle cx="32" cy="32" r="10"/>
    <!-- Gear teeth -->
    <path d="M42 30h4v4h-4zM18 30h4v4h-4zM32 18h4v4h-4zM32 42h4v4h-4zM45.1 45.1l2.8 2.8-2.8 2.8-2.8-2.8zM16.9 45.1l2.8 2.8-2.8 2.8-2.8-2.8zM45.1 16.9l2.8-2.8 2.8 2.8-2.8 2.8zM16.9 16.9l2.8-2.8 2.8 2.8-2.8 2.8z"/>
  </g>
</svg>"""

xfunction_icon = """<svg width="100" height="100" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" role="img" preserveAspectRatio="xMidYMid meet" fill="#000000">
  <!-- Circle background -->
  <circle cx="32" cy="32" r="30" fill="#875a7b" />

  <!-- Cog (gear) shape -->
  <path fill="#231815" d="M20,22.5c-1.4,0-2.5-1.1-2.5-2.5s1.1-2.5,2.5-2.5s2.5,1.1,2.5,2.5S21.4,22.5,20,22.5z M20,18.5
					c-0.8,0-1.5,0.7-1.5,1.5s0.7,1.5,1.5,1.5s1.5-0.7,1.5-1.5S20.8,18.5,20,18.5z"/>
  <path fill="#231815" d="M20.7,28.5h-1.3c-0.6,0-1.2-0.5-1.2-1.2v-1c-0.4-0.1-0.8-0.3-1.2-0.5c-0.1,0-0.2,0-0.2,0l-0.7,0.7
					c-0.4,0.4-1.2,0.4-1.7,0l-1-1c-0.5-0.5-0.5-1.2,0-1.7l0.7-0.7c0.1-0.1,0-0.2,0-0.2c-0.2-0.3-0.3-0.7-0.4-1
					c0-0.1-0.1-0.1-0.2-0.1h-0.9c-0.6,0-1.2-0.5-1.2-1.2v-1.3c0-0.6,0.5-1.2,1.2-1.2h0.9c0.1,0,0.1-0.1,0.2-0.1
					c0.1-0.4,0.3-0.7,0.4-1c0-0.1,0-0.1,0-0.2l-0.7-0.7c-0.5-0.5-0.5-1.2,0-1.7l1-1c0.4-0.4,1.2-0.4,1.7,0l0.7,0.7
					c0.1,0.1,0.1,0.1,0.2,0c0.3-0.2,0.7-0.3,1-0.4c0.1,0,0.1-0.1,0.1-0.2v-0.9c0-0.6,0.5-1.2,1.2-1.2h1.3c0.6,0,1.2,0.5,1.2,1.2v0.9
					c0,0.1,0.1,0.1,0.1,0.2c0.3,0.1,0.7,0.3,1,0.4c0.1,0,0.2,0,0.2,0l0.7-0.7c0.4-0.4,1.2-0.4,1.7,0l1,1c0.5,0.5,0.5,1.2,0,1.7
					l-0.7,0.7c-0.1,0.1,0,0.2,0,0.2c0.2,0.3,0.3,0.7,0.4,1c0,0.1,0.1,0.1,0.2,0.1h0.9c0.6,0,1.2,0.5,1.2,1.2v1.3
					c0,0.6-0.5,1.2-1.2,1.2h-0.9c-0.1,0-0.1,0.1-0.2,0.1c-0.1,0.4-0.3,0.7-0.4,1c0,0.1,0,0.1,0,0.2l0.7,0.7c0.5,0.5,0.5,1.2,0,1.7
					l-1,1c-0.4,0.4-1.2,0.4-1.7,0l-0.7-0.7c-0.1-0.1-0.1-0.1-0.2,0c-0.3,0.2-0.7,0.3-1,0.4c-0.1,0-0.1,0.1-0.1,0.2v0.9
					C21.8,28,21.3,28.5,20.7,28.5z M16.9,24.8c0.2,0,0.4,0,0.6,0.1c0.4,0.2,0.9,0.4,1.3,0.5c0.2,0.1,0.4,0.3,0.4,0.5v1.4
					c0,0.1,0.1,0.2,0.2,0.2h1.3c0.1,0,0.2-0.1,0.2-0.2v-0.9c0-0.5,0.3-1,0.8-1.1c0.3-0.1,0.6-0.2,0.9-0.4c0.5-0.2,1-0.2,1.4,0.2
					l0.7,0.7c0.1,0.1,0.2,0.1,0.2,0l1-1c0.1-0.1,0.1-0.2,0-0.2l-0.7-0.7c-0.4-0.4-0.4-0.9-0.2-1.4c0.1-0.3,0.3-0.6,0.4-0.9
					c0.2-0.5,0.6-0.8,1.1-0.8h0.9c0.1,0,0.2-0.1,0.2-0.2v-1.3c0-0.1-0.1-0.2-0.2-0.2h-0.9c-0.5,0-1-0.3-1.1-0.8
					c-0.1-0.3-0.2-0.6-0.4-0.9c-0.2-0.5-0.2-1,0.2-1.4l0.7-0.7c0.1-0.1,0.1-0.2,0-0.2l-1-1c-0.1-0.1-0.2-0.1-0.2,0l-0.7,0.7
					c-0.4,0.3-0.9,0.4-1.4,0.2c-0.3-0.1-0.6-0.3-0.9-0.4c-0.5-0.2-0.8-0.6-0.8-1.1v-0.9c0-0.1-0.1-0.2-0.2-0.2h-1.3
					c-0.1,0-0.2,0.1-0.2,0.2v0.9c0,0.5-0.3,1-0.8,1.1c-0.3,0.1-0.6,0.2-0.9,0.4c-0.5,0.2-1,0.2-1.4-0.2l-0.7-0.7
					c-0.1-0.1-0.2-0.1-0.2,0l-1,1c-0.1,0.1-0.1,0.2,0,0.2l0.7,0.7c0.4,0.4,0.4,0.9,0.2,1.4c-0.1,0.3-0.3,0.6-0.4,0.9
					c-0.2,0.5-0.6,0.8-1.1,0.8h-0.9c-0.1,0-0.2,0.1-0.2,0.2v1.3c0,0.1,0.1,0.2,0.2,0.2h0.9c0.5,0,1,0.3,1.1,0.8
					c0.1,0.3,0.2,0.6,0.4,0.9c0.2,0.5,0.2,1-0.2,1.4l-0.7,0.7c-0.1,0.1-0.1,0.2,0,0.2l1,1c0.1,0.1,0.2,0.1,0.2,0l0.7-0.7
					C16.3,24.9,16.6,24.8,16.9,24.8z"/>"""

function_icon = """<svg height="800px" width="800px" version="1.1" id="图层_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" 
	 viewBox="0 0 40 40" enable-background="new 0 0 40 40" xml:space="preserve">
<g>
	<g>
		<g>
			<g>
				<path fill="#875a7b" d="M20,22.5c-1.4,0-2.5-1.1-2.5-2.5s1.1-2.5,2.5-2.5s2.5,1.1,2.5,2.5S21.4,22.5,20,22.5z M20,18.5
					c-0.8,0-1.5,0.7-1.5,1.5s0.7,1.5,1.5,1.5s1.5-0.7,1.5-1.5S20.8,18.5,20,18.5z"/>
			</g>
			<g>
				<path fill="#231815" d="M20.7,28.5h-1.3c-0.6,0-1.2-0.5-1.2-1.2v-1c-0.4-0.1-0.8-0.3-1.2-0.5c-0.1,0-0.2,0-0.2,0l-0.7,0.7
					c-0.4,0.4-1.2,0.4-1.7,0l-1-1c-0.5-0.5-0.5-1.2,0-1.7l0.7-0.7c0.1-0.1,0-0.2,0-0.2c-0.2-0.3-0.3-0.7-0.4-1
					c0-0.1-0.1-0.1-0.2-0.1h-0.9c-0.6,0-1.2-0.5-1.2-1.2v-1.3c0-0.6,0.5-1.2,1.2-1.2h0.9c0.1,0,0.1-0.1,0.2-0.1
					c0.1-0.4,0.3-0.7,0.4-1c0-0.1,0-0.1,0-0.2l-0.7-0.7c-0.5-0.5-0.5-1.2,0-1.7l1-1c0.4-0.4,1.2-0.4,1.7,0l0.7,0.7
					c0.1,0.1,0.1,0.1,0.2,0c0.3-0.2,0.7-0.3,1-0.4c0.1,0,0.1-0.1,0.1-0.2v-0.9c0-0.6,0.5-1.2,1.2-1.2h1.3c0.6,0,1.2,0.5,1.2,1.2v0.9
					c0,0.1,0.1,0.1,0.1,0.2c0.3,0.1,0.7,0.3,1,0.4c0.1,0,0.2,0,0.2,0l0.7-0.7c0.4-0.4,1.2-0.4,1.7,0l1,1c0.5,0.5,0.5,1.2,0,1.7
					l-0.7,0.7c-0.1,0.1,0,0.2,0,0.2c0.2,0.3,0.3,0.7,0.4,1c0,0.1,0.1,0.1,0.2,0.1h0.9c0.6,0,1.2,0.5,1.2,1.2v1.3
					c0,0.6-0.5,1.2-1.2,1.2h-0.9c-0.1,0-0.1,0.1-0.2,0.1c-0.1,0.4-0.3,0.7-0.4,1c0,0.1,0,0.1,0,0.2l0.7,0.7c0.5,0.5,0.5,1.2,0,1.7
					l-1,1c-0.4,0.4-1.2,0.4-1.7,0l-0.7-0.7c-0.1-0.1-0.1-0.1-0.2,0c-0.3,0.2-0.7,0.3-1,0.4c-0.1,0-0.1,0.1-0.1,0.2v0.9
					C21.8,28,21.3,28.5,20.7,28.5z M16.9,24.8c0.2,0,0.4,0,0.6,0.1c0.4,0.2,0.9,0.4,1.3,0.5c0.2,0.1,0.4,0.3,0.4,0.5v1.4
					c0,0.1,0.1,0.2,0.2,0.2h1.3c0.1,0,0.2-0.1,0.2-0.2v-0.9c0-0.5,0.3-1,0.8-1.1c0.3-0.1,0.6-0.2,0.9-0.4c0.5-0.2,1-0.2,1.4,0.2
					l0.7,0.7c0.1,0.1,0.2,0.1,0.2,0l1-1c0.1-0.1,0.1-0.2,0-0.2l-0.7-0.7c-0.4-0.4-0.4-0.9-0.2-1.4c0.1-0.3,0.3-0.6,0.4-0.9
					c0.2-0.5,0.6-0.8,1.1-0.8h0.9c0.1,0,0.2-0.1,0.2-0.2v-1.3c0-0.1-0.1-0.2-0.2-0.2h-0.9c-0.5,0-1-0.3-1.1-0.8
					c-0.1-0.3-0.2-0.6-0.4-0.9c-0.2-0.5-0.2-1,0.2-1.4l0.7-0.7c0.1-0.1,0.1-0.2,0-0.2l-1-1c-0.1-0.1-0.2-0.1-0.2,0l-0.7,0.7
					c-0.4,0.3-0.9,0.4-1.4,0.2c-0.3-0.1-0.6-0.3-0.9-0.4c-0.5-0.2-0.8-0.6-0.8-1.1v-0.9c0-0.1-0.1-0.2-0.2-0.2h-1.3
					c-0.1,0-0.2,0.1-0.2,0.2v0.9c0,0.5-0.3,1-0.8,1.1c-0.3,0.1-0.6,0.2-0.9,0.4c-0.5,0.2-1,0.2-1.4-0.2l-0.7-0.7
					c-0.1-0.1-0.2-0.1-0.2,0l-1,1c-0.1,0.1-0.1,0.2,0,0.2l0.7,0.7c0.4,0.4,0.4,0.9,0.2,1.4c-0.1,0.3-0.3,0.6-0.4,0.9
					c-0.2,0.5-0.6,0.8-1.1,0.8h-0.9c-0.1,0-0.2,0.1-0.2,0.2v1.3c0,0.1,0.1,0.2,0.2,0.2h0.9c0.5,0,1,0.3,1.1,0.8
					c0.1,0.3,0.2,0.6,0.4,0.9c0.2,0.5,0.2,1-0.2,1.4l-0.7,0.7c-0.1,0.1-0.1,0.2,0,0.2l1,1c0.1,0.1,0.2,0.1,0.2,0l0.7-0.7
					C16.3,24.9,16.6,24.8,16.9,24.8z"/>
			</g>
		</g>
	</g>
</g>
</svg>"""


class PrdFunction(models.Model):
    _name = 'prd.function'
    _inherit = ['mermaid.mixin', 'mail.thread', 'mail.activity.mixin', 'prd.odoo_module.mixin']
    _description = 'PRD Functions'

    # models / data / sequrity / sequirity.xml / views /
    active = fields.Boolean(string='Active', default=True)
    avatar_128 = fields.Image("Avatar", max_width=128, max_height=128, compute='_compute_avatar_128')
    category_ids = fields.Many2many(
        comodel_name='prd.function_category',
        string='Tags',
        help="Categories"
    )
    description = fields.Text(string="Description")
    duration_tracking = fields.Float(string='Duration Tracking')
    func_type = fields.Many2one(comodel_name='prd.function_type', string="Type", help="")
    input_data = fields.Text(string="Input")
    module_prd_id = fields.Many2one(comodel_name='prd.document', string="Product Requirement Document", help="")
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
    weight = fields.Selection(
    selection=[
        ('1', 'Easy'),
        ('2', 'Medium'),
        ('4', 'Hard'),
        ('8', 'Very hard'),
    ],
    string="Weight",
    default='1',
        )

    requirement_names_ids = fields.Many2many(
        comodel_name='prd.requirement', string="Requirement", compute='_compute_requirement_names_ids'
    )

    @api.depends('requirement_ids.func_id')
    def _compute_requirement_names_ids(self):
        for record in self:
            record.requirement_names_ids = record.requirement_ids.mapped('req_id')

    sequence = fields.Integer(string='Sequence')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ongoing', 'Ongoing'),
        ('done', 'Done')
    ], string="State", default='draft')
    to_check = fields.Boolean()
    user_id = fields.Many2one(comodel_name='res.users', string="Author", help="")
    implementation_type = fields.Selection(
        related="func_type.implementation_type",
        string="Implementation Type",
        readonly=True,
        store=False,
    )
    color = fields.Integer(default=lambda self: randint(1, 11))
    image_128 = fields.Image("Image", max_width=128, max_height=128)

    @api.model
    def _generate_random_token(self):
        return ''.join(choice('abcdefghijkmnopqrstuvwxyzABCDEFGHIJKLMNPQRSTUVWXYZ23456789') for _i in range(10))

    uuid = fields.Char('UUID', size=50, default=_generate_random_token, copy=False)

    @api.depends('image_128', 'uuid')
    def _compute_avatar_128(self):
        for record in self:
            if record.image_128:
                record.avatar_128 = record.image_128
            else:
                record.avatar_128 = record._generate_avatar()

    def _generate_avatar(self):
        avatar = function_icon
        bgcolor = get_hsl_from_seed(self.uuid)
        avatar = avatar.replace('fill="#875a7b"', f'fill="{bgcolor}"')
        return base64.b64encode(avatar.encode())


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
    implementation_type = fields.Selection(
        selection=[('module', 'Module'), ('odoo_module', 'Odoo Module'), ('prd', 'Product Requirement Document'),
                   ('other', 'Other')], string='Type', default="other", required=True)


class FunctionCategory(models.Model):
    _name = 'prd.function_category'
    _description = 'Function Category'

    name = fields.Char(string='Category', required=True)
    color = fields.Integer(string='Color', default=lambda self: randint(0, 10))
    active = fields.Boolean(string='Active', default=True)


class OdooRepo(models.Model):
    _name = 'prd.odoo_branch'
    _description = 'Odoo Branch'

    name = fields.Char(string='Name', required=True)


class OdooRepo(models.Model):
    _name = 'prd.odoo_repo'
    _description = 'Odoo Repository'

    name = fields.Char(string='Name', required=True)
    url = fields.Char(string='URL', help='url eg "https://api.github.com/repos/{self.owner}/{self.name}/git/trees/{branch_id.name}?recursive=1"')
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

    def list_files(self,branch_id):
        # url = f"https://api.github.com/repos/{self.owner}/{self.name}/git/trees/{branch_id.name}?recursive=1"
        resp = requests.get(eval(self.url))
        resp.raise_for_status()
        data = resp.json()
        files = []
        for item in data.get("tree", []):
            if item["type"] == "blob":
                files.append({"path": item["path"], "sha": item["sha"], 'branch': branch_id.name})
        return files

    @api.model
    def get_file_content(self,file):
        resp = requests.get(file['url'])
        resp.raise_for_status()
        blob = resp.json()
        content_b64 = blob["content"].replace("\n", "")
        decoded_bytes = base64.b64decode(content_b64)
        text = decoded_bytes.decode(encoding, errors="replace")
        return text
        
    def get_branch(self):
        """Get all branches for this repo"""
        self.ensure_one()
        if self.repo_source == 'github':
            # GitHub API: https://api.github.com/repos/{owner}/{repo}/branches
            url = f"https://api.github.com/repos/{self.owner}/{self.name}/branches"
        elif self.repo_source == 'gitlab':
            # GitLab API: https://gitlab.com/api/v4/projects/{owner}%2F{repo}/repository/branches
            url = f"https://gitlab.com/api/v4/projects/{self.owner}%2F{self.name}/repository/branches"
        else:
            return []
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            branches = resp.json()
            
            branch_data = []
            for branch in branches:
                if self.repo_source == 'github':
                    name = branch['name']
                    commit_sha = branch['commit']['sha']
                else:  # gitlab
                    name = branch['name']
                    commit_sha = branch['commit']['id']
                b = self.env['ord.odoo_branch'].search([('name','=',name)],limit=1)
                if not b:
                    b = self.env['ord.odoo_branch'].create({'name': name})
                self.branch_ids = [(6,0,[b.id])]
                branch_data.append({
                    'name': name,
                    'commit_sha': commit_sha,
                    'url': branch.get('links', {}).get('html', f"https://github.com/{self.owner}/{self.name}/tree/{name}")
                })
            return branch_data
        except requests.exceptions.RequestException as e:
            _logger.error(f"Failed to fetch branches for {self.name}: {e}")
            return []
        except Exception as e:
            _logger.error(f"Error processing branches for {self.name}: {e}")
            return []

class OdooModule(models.Model):
    _name = 'prd.odoo_module'
    _inherit = ['prd.odoo_module.mixin']
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


class OdooViewType(models.Model):
    _name = 'prd.odoo_view_type'
    _description = 'Odoo View Type'

    name = fields.Char(string='View Type Name', required=True)
    code = fields.Char(string='View Type Code', required=True)
    description = fields.Text(string='Description')
    prompt = fields.Text(string='Prompt')
    active = fields.Boolean(string='Active', default=True)
