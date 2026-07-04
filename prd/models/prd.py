from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError
import re
import html
from bs4 import BeautifulSoup

import logging

_logger = logging.getLogger(__name__)

from odoo import models, fields


class PrdStakeholder(models.Model):
    _name = "prd.stakeholder"
    _description = "PRD Stakeholder"
    _order = "sequence, id"

    name = fields.Char(string="Name", required=True)
    partner_id = fields.Many2one(
        "res.partner", string="Contact", ondelete="set null"
    )
    user_id = fields.Many2one(
        "res.users", string="User", ondelete="set null"
    )
    role = fields.Selection(
        [
            ("reviewer", "Reviewer"),
            ("approver", "Approver"),
            ("consulted", "Consulted"),
            ("informed", "Informed"),
            ("responsible", "Responsible"),
        ],
        string="Role",
        default="reviewer",
        required=True,
    )
    sign_off_state = fields.Selection(
        [
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("not_required", "Not Required"),
        ],
        string="Sign-off",
        default="pending",
        tracking=True,
    )
    sign_off_date = fields.Datetime(string="Sign-off Date", readonly=True)
    sign_off_comment = fields.Text(string="Comment")
    prd_id = fields.Many2one(
        "prd.document", string="PRD", ondelete="cascade", required=True
    )
    sequence = fields.Integer(string="Sequence", default=10)

    def action_approve(self):
        self.write({
            "sign_off_state": "approved",
            "sign_off_date": fields.Datetime.now(),
        })

    def action_reject(self):
        self.write({
            "sign_off_state": "rejected",
            "sign_off_date": fields.Datetime.now(),
        })


class PrdTemplate(models.Model):
    _name = "prd.template"
    _description = "PRD Template"
    _order = "sequence, name"

    name = fields.Char(string="Name", required=True)
    description = fields.Text(string="Description")
    document_type = fields.Selection(
        [
            ("module", "Module"),
            ("procurement", "Procurement/call-off"),
            ("other", "Other"),
        ],
        string="Type",
        default="module",
        required=True,
    )
    goals = fields.Text(string="Default Goals")
    user_persona = fields.Text(string="Default User Persona")
    use_cases = fields.Text(string="Default Use Cases")
    success_criteria = fields.Text(string="Default Success Criteria")
    risks = fields.Text(string="Default Risks")
    default_requirements = fields.Text(
        string="Default Requirements",
        help="One requirement per line. Format: CODE|Name|Description|Priority"
    )
    active = fields.Boolean(string="Active", default=True)
    sequence = fields.Integer(string="Sequence", default=10)

    def create_prd_from_template(self):
        """Create a new PRD from this template."""
        self.ensure_one()
        vals = {
            "name": f"{self.name} - Copy",
            "document_type": self.document_type,
            "goals": self.goals,
            "user_persona": self.user_persona,
            "use_cases": self.use_cases,
            "success_criteria": self.success_criteria,
            "risks": self.risks,
        }
        prd = self.env["prd.document"].create(vals)

        # Parse default requirements
        if self.default_requirements:
            for line in self.default_requirements.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                parts = line.split("|")
                code = parts[0].strip() if len(parts) > 0 else ""
                name = parts[1].strip() if len(parts) > 1 else ""
                desc = parts[2].strip() if len(parts) > 2 else ""
                priority = parts[3].strip() if len(parts) > 3 else "must"
                self.env["prd.requirement"].create({
                    "prd_id": prd.id,
                    "code": code,
                    "name": name or code,
                    "description": desc,
                    "priority": priority if priority in ("must", "should", "could") else "must",
                })

        return {
            "type": "ir.actions.act_window",
            "res_model": "prd.document",
            "res_id": prd.id,
            "view_mode": "form",
            "target": "current",
        }


class ProductRequirementDocument(models.Model):
    _name = "prd.document"
    _inherit = [
        "mermaid.mixin",
        "mail.thread",
        "mail.activity.mixin",
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
    template_id = fields.Many2one(
        "prd.template", string="Created From Template", readonly=True, ondelete="set null"
    )
    stakeholder_ids = fields.One2many(
        "prd.stakeholder", "prd_id", string="Stakeholders"
    )
    stakeholders_approved_count = fields.Integer(
        string="Approvals", compute="_compute_stakeholder_counts"
    )
    stakeholders_total_count = fields.Integer(
        string="Total Stakeholders", compute="_compute_stakeholder_counts"
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

    @api.depends("stakeholder_ids", "stakeholder_ids.sign_off_state")
    def _compute_stakeholder_counts(self):
        for record in self:
            approvers = record.stakeholder_ids.filtered(
                lambda s: s.role == "approver"
            )
            record.stakeholders_total_count = len(record.stakeholder_ids)
            record.stakeholders_approved_count = len(
                approvers.filtered(lambda s: s.sign_off_state == "approved")
            )

    def action_submit_review(self):
        self.state = "in_review"

    def action_approve(self):
        self.state = "approved"
        self.approved_by_id = self.env.user.id
        self.date = fields.Date.today()

    def action_reject(self):
        self.state = "rejected"

    def action_mark_implemented(self):
        self.state = "implemented"

    def action_mark_verified(self):
        self.state = "verified"

    def action_traceability_matrix(self):
        """Return action for traceability matrix view."""
        return {
            "type": "ir.actions.act_window",
            "name": "Traceability Matrix",
            "res_model": "prd.traceability",
            "view_mode": "tree",
            "domain": [("prd_id", "=", self.id)],
            "context": {"search_default_group_by_requirement": 1},
            "target": "current",
        }

    def _generate_traceability_data(self):
        """Generate traceability matrix data."""
        self.ensure_one()
        Traceability = self.env["prd.traceability"]
        # Clear existing
        self.env["prd.traceability"].search([("prd_id", "=", self.id)]).unlink()

        for req in self.requirement_ids:
            # Find functions linked to this requirement
            linked_funcs = req.function_ids.mapped("func_id")
            if not linked_funcs:
                Traceability.create({
                    "prd_id": self.id,
                    "requirement_id": req.id,
                    "function_id": False,
                    "task_id": False,
                })
            for func in linked_funcs:
                # Find tasks linked to this function
                tasks = func.task_id if hasattr(func, "task_id") and func.task_id else False
                if not tasks:
                    Traceability.create({
                        "prd_id": self.id,
                        "requirement_id": req.id,
                        "function_id": func.id,
                        "task_id": False,
                    })
                else:
                    Traceability.create({
                        "prd_id": self.id,
                        "requirement_id": req.id,
                        "function_id": func.id,
                        "task_id": tasks.id if hasattr(tasks, "id") else False,
                    })

        return self.action_traceability_matrix()

    def action_stakeholders(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Stakeholders",
            "res_model": "prd.stakeholder",
            "domain": [("prd_id", "=", self.id)],
            "context": {"default_prd_id": self.id},
            "view_mode": "tree,form",
            "target": "current",
        }

    @api.depends("function_ids", "function_ids.state")
    def _compute_functions_counts(self):
        for record in self:
            total = len(record.function_ids)
            closed = len(record.function_ids.filtered(
                lambda f: f.state in ("done", "verified", "implemented")
            ))
            record.functions_count = total
            record.closed_functions_count = closed
            record.functions_percentage = (closed / total) if total else 0.0

    @api.depends("requirement_ids", "requirement_ids.state")
    def _compute_requirements_counts(self):
        for record in self:
            total = len(record.requirement_ids)
            closed = len(record.requirement_ids.filtered(
                lambda r: r.state in ("done", "verified", "implemented")
            ))
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
