from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class PrdTraceability(models.Model):
    """Traceability Matrix — maps Requirements → Functions → Tasks.

    This is a transient model that stores computed traceability data.
    The action _generate_traceability_data() on prd.document builds
    the matrix and opens this view.
    """
    _name = "prd.traceability"
    _description = "PRD Traceability Matrix"
    _order = "requirement_code, function_name"

    prd_id = fields.Many2one(
        "prd.document", string="PRD", required=True, ondelete="cascade"
    )
    requirement_id = fields.Many2one(
        "prd.requirement", string="Requirement", ondelete="cascade"
    )
    requirement_code = fields.Char(related="requirement_id.code", string="Req #")
    requirement_name = fields.Char(related="requirement_id.name", string="Requirement")
    requirement_state = fields.Selection(related="requirement_id.state", string="Req State")
    requirement_priority = fields.Selection(related="requirement_id.priority", string="Priority")

    function_id = fields.Many2one(
        "prd.function", string="Function", ondelete="cascade"
    )
    function_name = fields.Char(related="function_id.name", string="Function")
    function_state = fields.Selection(related="function_id.state", string="Func State")

    task_id = fields.Many2one(
        "project.task", string="Task", ondelete="set null"
    )
    task_name = fields.Char(related="task_id.name", string="Task")
    task_stage_id = fields.Many2one(related="task_id.stage_id", string="Task Stage")

    coverage_status = fields.Selection(
        [
            ("full", "Full Coverage"),
            ("partial", "Partial — No Task"),
            ("none", "No Coverage"),
        ],
        string="Coverage",
        compute="_compute_coverage_status",
        store=True,
    )

    @api.depends("function_id", "task_id")
    def _compute_coverage_status(self):
        for record in self:
            if record.function_id and record.task_id:
                record.coverage_status = "full"
            elif record.function_id:
                record.coverage_status = "partial"
            else:
                record.coverage_status = "none"
