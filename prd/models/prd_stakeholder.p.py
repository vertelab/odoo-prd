from odoo import api, fields, models, _
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class PrdStakeholder(models.Model):
    """Stakeholder for PRD sign-off and review tracking."""

    _name = "prd.stakeholder"
    _inherit = ["mail.thread"]
    _description = "PRD Stakeholder"
    _order = "sequence, name"

    name = fields.Char(string="Name", required=True)
    partner_id = fields.Many2one(
        "res.partner", string="Contact", ondelete="set null"
    )
    user_id = fields.Many2one(
        "res.users", string="User", ondelete="set null"
    )
    prd_id = fields.Many2one(
        "prd.document", string="PRD", required=True, ondelete="cascade"
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
        ],
        string="Sign-off State",
        default="pending",
        required=True,
        tracking=True,
    )
    sign_off_date = fields.Date(
        string="Sign-off Date", readonly=True, tracking=True
    )
    sign_off_comment = fields.Text(string="Sign-off Comment")
    sequence = fields.Integer(string="Sequence", default=10)

    def action_approve(self):
        for record in self:
            record.write({
                "sign_off_state": "approved",
                "sign_off_date": fields.Date.today(),
            })

    def action_reject(self):
        for record in self:
            record.write({
                "sign_off_state": "rejected",
                "sign_off_date": fields.Date.today(),
            })
