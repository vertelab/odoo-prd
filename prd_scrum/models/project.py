import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError

_logger = logging.getLogger(__name__)

class ProjectUserStories(models.Model):
    _inherit = 'project.scrum.us'
    
    doc_id = fields.Many2one(comodel_name="prd.document")
    func_id = fields.Many2one(comodel_name='prd.function',string="Function",help="")

class ProjectTask(models.Model):
    _inherit = 'project.task'

    func_ids = fields.One2many(comodel_name='prd.function',compute='_compute_func_ids',string="Function",help="")
    func_count = fields.Integer(compute="_compute_func_ids")

    def _compute_func_ids(self):
        self.ensure_one()
        func_ids = self.env["prd.function"].search([("task_id", "=", self.id)])
        self.func_ids = func_ids
        self.func_count = len(func_ids)

    def action_get_funcs(self):
        return {
                'type': 'ir.actions.act_window',
                'res_model': 'ir.attachment',
                'views': [(False,'list'),(False,'form')],
                'target': 'current',
                'domain': [("id", "in", self.func_ids.ids)]
            }



