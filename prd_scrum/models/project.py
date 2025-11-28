import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError

_logger = logging.getLogger(__name__)

class ProjectUserStories(models.Model):
    _inherit = 'project.scrum.us'
    
    function_us_ids = fields.One2many(comodel_name='prd.function.us',inverse_name="user_story_id",string="Function",help="")

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        stage_ids = super(ProjectUserStories,self)._read_group_stage_ids(stages,domain)
        
        if prd_id := self.env.context.get("prd_id"):
            prd_id = self.env["prd.document"].browse(prd_id)
            stage_ids = self.env["project.task.type"].search([("project_ids", "in", prd_id.project_id.ids)])
            _logger.error(f"{stage_ids=}")
            return stage_ids

        return stage_ids

class ProjectTask(models.Model):
    _inherit = 'project.task'

    func_ids = fields.One2many(comodel_name='prd.function',compute='_compute_func_ids',string="Function",help="")
    func_count = fields.Integer(compute="_compute_func_ids")
    req_ids = fields.One2many(comodel_name="prd.requirement", compute="_compute_req_ids")
    req_count = fields.Integer(compute="_compute_req_ids")

    def _compute_func_ids(self):
        for rec in self:       
            func_ids = rec.env["prd.function"].search([("task_id", "=", rec.id)])
            rec.func_ids = func_ids
            rec.func_count = len(func_ids)
    
    def _compute_req_ids(self):
        for rec in self:
            func_ids = rec.env["prd.function"].search([("task_id", "=", rec.id)])
            req_task_ids = func_ids.mapped("requirement_ids")
            req_ids = req_task_ids.mapped("req_id")
            rec.req_ids = req_ids
            rec.req_count = len(req_ids)

    def action_get_funcs(self):
        return {
                'type': 'ir.actions.act_window',
                'res_model': 'prd.function',
                'views': [(False,'list'),(False,'form')],
                'target': 'current',
                'domain': [("id", "in", self.func_ids.ids)]
            }
    
    def action_get_reqs(self):
        return {
                'type': 'ir.actions.act_window',
                'res_model': 'prd.requirement',
                'views': [(False,'list'),(False,'form')],
                'target': 'current',
                'domain': [("id", "in", self.req_ids.ids)]
            }



