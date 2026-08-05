from odoo import api, fields, models, _
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class PrdTemplate(models.Model):
    """PRD Template for standardizing requirement documents."""

    _name = "prd.template"
    _description = "PRD Template"
    _order = "sequence, name"

    name = fields.Char(string="Name", required=True)
    active = fields.Boolean(string="Active", default=True)
    sequence = fields.Integer(string="Sequence", default=10)
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
    description = fields.Text(string="Description")
    goals = fields.Text(string="Goals")
    user_persona = fields.Text(string="User Persona")
    use_cases = fields.Text(string="Use Cases")
    success_criteria = fields.Text(string="Success Criteria")
    risks = fields.Text(string="Risks")
    default_requirements = fields.Text(
        string="Default Requirements",
        help="CODE|Name|Description|Priority, one per line",
    )

    def create_prd_from_template(self):
        """Create a PRD document pre-filled with template values."""
        self.ensure_one()
        Prd = self.env["prd.document"]
        Req = self.env["prd.requirement"]

        prd = Prd.create({
            "name": _("PRD from %s", self.name),
            "document_type": self.document_type,
            "description": self.description,
            "goals": self.goals,
            "user_persona": self.user_persona,
            "use_cases": self.use_cases,
            "success_criteria": self.success_criteria,
            "risks": self.risks,
        })

        if self.default_requirements:
            for line in self.default_requirements.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                parts = line.split("|", 3)
                code = parts[0].strip() if len(parts) > 0 else ""
                name = parts[1].strip() if len(parts) > 1 else ""
                desc = parts[2].strip() if len(parts) > 2 else ""
                priority = parts[3].strip() if len(parts) > 3 else "should"

                Req.create({
                    "prd_id": prd.id,
                    "code": code,
                    "name": name or code,
                    "description": desc,
                    "priority": priority,
                })

        return {
            "type": "ir.actions.act_window",
            "res_model": "prd.document",
            "res_id": prd.id,
            "view_mode": "form",
            "target": "current",
        }
