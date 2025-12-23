from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError
import logging

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
        for file in self.repo_id.get_files(self.branch_id.name):
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
        ('models','Model'),
        ('report','Report'),
        ('security','Security'),
        ('static','Static'),
        ('tests','Tests'),
        ('views','Views'),
        ('wizard','Wizard'),
        ('other','Other'),
            ],string='Type')
    content = fields.Text(string='Content')

    def get_modules_files(self,module):
        for file in module.repo_id.get_files(self.branch_id.name):
            self._create_update(file,module)

    @api.model
    def _create_update(self,file,module):
        ft = 'other'
        for file_type in dict(self._fields['file_type'].selection).keys():
            if file_type in file:
                ft = file_type
        vals = {
            # ~ 'name': file['path'].split('/')[-1],
            'name': file,
            'module_id': module.id,
            # ~ 'git_url': file['url'],
            'file_type': ft,
            # ~ 'content': module.repo_id.get_file_content(file,module.branch_id.name),
            # ~ 'path': file['path'], 
        }
        file_rec = self.env['prd.odoo_module.file'].search([
            ('module_id', '=', module.id), 
            ('name', '=', file)
        ], limit=1)
        if file_rec:
            file_rec.write(vals)
        else:
            self.env['prd.odoo_module.file'].create(vals)

                
    # ~ {
        # ~ "sha": "10d4dafbd2ae5c0478a7563352e9ef850f6a2cd2",
        # ~ "url": "https://api.github.com/repos/vertelab/odoo-prd/git/trees/10d4dafbd2ae5c0478a7563352e9ef850f6a2cd2",
        # ~ "tree": [
 
    # ~ {
      # ~ "path": "prd_scrum/views/project_views.xml",
      # ~ "mode": "100644",
      # ~ "type": "blob",
      # ~ "sha": "754639b30dc8410dccec520a684d7947e23c7971",
      # ~ "size": 1313,
      # ~ "url": "https://api.github.com/repos/vertelab/odoo-prd/git/blobs/754639b30dc8410dccec520a684d7947e23c7971"
    # ~ },

            
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
