from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError
import logging

_logger = logging.getLogger(__name__)

class PrdFunction(models.Model):
    _inherit = 'prd.function'

    # scrum_us_ids = fields.One2many(comodel_name='project.scrum.us', inverse_name='func_id')
    function_us_ids = fields.One2many(comodel_name='prd.function.us', inverse_name='function_id')
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

class PrdFunctionUS(models.Model):
    _name = "prd.function.us"
    _description = "A glue model between prd.function and project.scrum.us"

    user_story_id = fields.Many2one(comodel_name="project.scrum.us")
    function_id = fields.Many2one(comodel_name="prd.function")
    sequence = fields.Integer()
    # name = 
    #           <field name="name" />
    #           <field name="actor_ids" widget="many2many_tags" />
    #           <field name="project_id" />
    #           <field name="stage_id"