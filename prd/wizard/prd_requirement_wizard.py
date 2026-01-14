import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError

_logger = logging.getLogger(__name__)


class PrdRequirementWizard(models.TransientModel):
    _name = "prd.requirement.wizard"
    _description = "PRD Requirement Wizard"

    user_id = fields.Many2one(
        comodel_name="res.users", string="Responsible", required=True
    )
    requirement_ids = fields.Many2many(comodel_name="prd.requirement")

    def set_responsible(self):
        for req_id in self.requirement_ids:
            req_id.write({"user_id": self.user_id.id})
