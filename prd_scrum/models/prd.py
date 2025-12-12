from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError
import logging

_logger = logging.getLogger(__name__)

class ProductRequirementDocument(models.Model):
    _inherit = 'prd.document'
   
    project_id = fields.Many2one(comodel_name='project.project',string="Project",help="In this project functions may have tasks") 
    scrum_us_ids = fields.One2many(
        comodel_name='project.scrum.us',
        compute='_compute_scrum_us_ids',
        string='User Stories',
        store=False
    )
    scrum_us_count = fields.Integer(compute='_scrum_us_count', string="User Stories", store=False)
    task_ids = fields.One2many(comodel_name='project.task',compute='_compute_task_ids',string="Tasks",help="")
    task_count = fields.Integer(compute='_task_count', string="Tasks")

    @api.depends("scrum_us_ids")
    def _scrum_us_count(self):
        for p in self:
            p.scrum_us_count = 0
            if p.scrum_us_ids:
                p.scrum_us_count = len(p.scrum_us_ids)

    @api.depends('function_ids')  
    def _compute_scrum_us_ids(self):
        for doc in self:
            function_us_ids = doc.env["prd.function.us"].search([("function_id", "in", doc.function_ids.ids)])
            user_story_ids = function_us_ids.mapped("user_story_id")
            doc.scrum_us_ids = user_story_ids

    @api.depends('function_ids')  
    def _compute_task_ids(self):
        for doc in self:
            task_ids = doc.function_ids.mapped("task_id")
            doc.task_ids = task_ids

    def _task_count(self):
        for p in self:
            p.task_count = len(p.task_ids)
            
    def action_user_stories(self):
        return {
          'type': 'ir.actions.act_window',
          'name': 'User Stories',
          'res_model': 'project.scrum.us',
          'domain': [('id', 'in', self.scrum_us_ids.ids)],
          'context': {"prd_id": self.id,'create_stage_allowed': False,'search_default_group_by_stage_id': 1},
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



