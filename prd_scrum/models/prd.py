from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError
import logging

_logger = logging.getLogger(__name__)

class ProductRequirementDocument(models.Model):
    _inherit = 'prd.document'
   
    project_id = fields.Many2one(comodel_name='project.project',string="Project",help="In this project functions may have tasks") 
    scrum_us_ids = fields.One2many(
        comodel_name='project.scrum.us',
        # inverse_name="doc_id",
        compute='_compute_scrum_us_ids',
        string='User Stories',
        store=False
    )

    @api.depends('function_ids.scrum_us_ids')  
    def _compute_scrum_us_ids(self):
        for doc in self:
            scrum_us_ids = doc.env['project.scrum.us'].search([
                ('func_id.prd_id', '=', doc.id)
            ])
            if scrum_us_ids:
                doc.scrum_us_ids = scrum_us_ids
            else:
                doc.scrum_us_ids = False

    scrum_us_count = fields.Integer(compute = '_scrum_us_count', string="User Stories")
    def _scrum_us_count(self):
        for p in self:
            p.scrum_us_count = len(p.scrum_us_ids)
    task_ids = fields.One2many(comodel_name='project.task',compute='_compute_task_ids',string="Tasks",help="") 

    @api.depends('function_ids.task_id')  
    def _compute_task_ids(self):
        for doc in self:
            doc.task_ids = doc.function_ids.mapped('task_id')

    task_count = fields.Integer(compute = '_task_count', string="Tasks")
    def _task_count(self):
        for p in self:
            p.task_count = len(p.task_ids)
            
    def action_user_stories(self):
        return {
          'type': 'ir.actions.act_window',
          'name': 'User Stories',
          'res_model': 'project.scrum.us',
          'domain': [('func_id.prd_id', '=', self.id)],
          'context': {'default_func_id': self.function_ids.ids[0] if self.function_ids else False},
          'view_mode': 'kanban,list,form', 
          'target': 'current',
      }

    def action_tasks(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tasks',
            'res_model': 'project.task',
            'domain': [('id', 'in', self.task_ids.ids)],
            'view_mode': 'kanban,list,form',
            'target': 'current',
        }


class PrdFunction(models.Model):
    _inherit = 'prd.function'

    scrum_us_ids = fields.One2many(comodel_name='project.scrum.us', inverse_name='func_id')
    task_id = fields.Many2one(comodel_name='project.task',string="Task",help="")
    
    def action_user_stories(self):
      return {
          'type': 'ir.actions.act_window',
          'name': 'User Stories',
          'res_model': 'project.scrum.us',
          'domain': [('func_id', '=', self.id)],
          'context': {'default_prd_id': self.id},
          'view_mode': 'kanban,list,form', 
          'target': 'current',
      }

class FunctionTypes(models.Model):
    _inherit = 'prd.function_type'
    
    implementation_type = fields.Selection(selection_add=[('task','Task'),],ondelete={'task': 'cascade', })


