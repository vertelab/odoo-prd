from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError
import re
import html
from bs4 import BeautifulSoup

import logging

_logger = logging.getLogger(__name__)

from odoo import models, fields


class ProductRequirementDocument(models.Model):
    _name = "prd.document"
    _inherit = [
        "mermaid.mixin",
        "mail.thread",
        "mail.activity.mixin",
        "prd.odoo_module.mixin",
    ]
    _description = "Product Requirement Document"
    _order = "sequence desc, name desc"

    avatar_128 = fields.Image(
        "Avatar",
        max_width=128,
        max_height=128,
    )
    duration_tracking = fields.Float(string="Duration Tracking")
    active = fields.Boolean(string="Active", default=True)
    parent_id = fields.Many2one(
        comodel_name="prd.document", string="Parent PRD", help="", ondelete="set null"
    )
    company_id = fields.Many2one(
        comodel_name="res.company", string="Company", help="", ondelete="set null"
    )
    name = fields.Char(string="Titel", required=True)
    # ~ summary = fields.Char(string="Summary", required=True)
    description = fields.Text(string="Description", help="Purpuse")
    version = fields.Char(string="Version", default="1.0", readonly=True, tracking=True)
    author_id = fields.Many2one(
        "res.users", string="Author", tracking=True, ondelete="set null"
    )
    product_owner_id = fields.Many2one(
        "res.users", string="Product Owner", tracking=True, ondelete="set null"
    )
    approved_by_id = fields.Many2one(
        "res.users",
        string="Approved By",
        readonly=True,
        tracking=True,
        ondelete="set null",
    )
    date = fields.Date(
        string="Date", default=fields.Date.today, readonly=True, tracking=True
    )
    goals = fields.Text(string="Goal")
    user_persona = fields.Text(string="Användarbeskrivning")
    use_cases = fields.Text(string="Användningsfall")
    success_criteria = fields.Text(string="Success Criteria")
    dependencies = fields.Text(string="Module Dependencies")
    risks = fields.Text(string="Risks")
    document_type = fields.Selection(
        [
            ("module", "Module"),
            ("procurement", "Procurement/call-off"),
            ("other", "Other"),
        ],
        string="Type",
        default="module",
    )
    state = fields.Selection(
        [("draft", "Draft"), ("approved", "Approved"), ("rejected", "Rejected")],
        string="State",
        default="draft",
        tracking=True,
    )
    requirement_ids = fields.One2many(
        comodel_name="prd.requirement",
        inverse_name="prd_id",
        string="Requirements",
        help="",
    )
    function_ids = fields.One2many(
        comodel_name="prd.function", inverse_name="prd_id", string="Functions", help=""
    )

    requirements_count = fields.Integer(
        string="Total Requirements", compute="_compute_requirements_counts"
    )
    closed_requirements_count = fields.Integer(
        string="Closed Requirements", compute="_compute_requirements_counts"
    )
    requirements_percentage = fields.Float(
        string="Requirements Completion %", compute="_compute_requirements_counts"
    )

    functions_count = fields.Integer(
        string="Total Functions", compute="_compute_functions_counts"
    )
    closed_functions_count = fields.Integer(
        string="Closed Functions", compute="_compute_functions_counts"
    )
    functions_percentage = fields.Float(
        string="Functions Completion %", compute="_compute_functions_counts"
    )
    tender_id = fields.Char(
        string="Tender ID",
        size=64,
        trim=True,
    )
    sequence = fields.Integer(string="Sequence")

    @api.onchange("state")
    def _onchange_state(self):
        if self.state == "approved":
            self.approved_by_id = self.env.user.id
            self.date = fields.Date.today()
        else:
            self.approved_by_id = False

    @api.depends("function_ids")
    def _compute_functions_counts(self):
        for record in self:
            total = len(record.function_ids)
            closed = len(record.function_ids.filtered(lambda f: f.state == "done"))
            record.functions_count = total
            record.closed_functions_count = closed
            record.functions_percentage = (closed / total) if total else 0.0

    @api.depends("requirement_ids")
    def _compute_requirements_counts(self):
        for record in self:
            total = len(record.requirement_ids)
            closed = len(record.requirement_ids.filtered(lambda r: r.state == "done"))
            record.requirements_count = total
            record.closed_requirements_count = closed
            record.requirements_percentage = 0.0
            if total > 0:
                record.requirements_percentage = closed / total

    @api.depends(
        "icon",
    )
    def _compute_avatar_128(self):
        for record in self:
            if record.icon:
                record.avatar_128 = record.icon

    def button_minor_version(self):
        for record in self:
            major, minor = record.version.split(".")
            # Increment minor
            minor = str(int(minor) + 1)
            record.version = f"{major}.{minor}"
            record.date = fields.Date.today()

    def button_major_version(self):
        for record in self:
            major, minor = record.version.split(".")
            # Increment major and reset minor to 0
            major = str(int(major) + 1)
            record.version = f"{major}.0"
            record.date = fields.Date.today()

    def action_functions(self):
        action = {
            "type": "ir.actions.act_window",
            "name": "Functions",
            "res_model": "prd.function",
            "domain": [("prd_id", "=", self.id)],
            "context": {"default_prd_id": self.id},
            "target": "current",
        }
        if self.functions_count > 0:
            action.update({"view_mode": "list,form,kanban"})
        else:
            action.update({"view_mode": "form,list,kanban"})
        return action

    def action_requirements(self):
        action = {
            "type": "ir.actions.act_window",
            "name": "Requirements",
            "res_model": "prd.requirement",
            "domain": [("prd_id", "=", self.id)],
            "context": {"default_prd_id": self.id},
            "target": "current",
        }
        if self.requirements_count > 0:
            action.update({"view_mode": "list,form"})
        else:
            action.update({"view_mode": "form,list"})
        return action
