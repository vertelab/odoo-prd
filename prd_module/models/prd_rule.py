import logging
from datetime import datetime, timedelta 

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError

_logger = logging.getLogger(__name__)

class PrdRule(models.Model):
    _name = 'prd.rule'
    _inherit = "ir.rule"
    _description = 'PRD rulse for modules'

    prd_id = fields.Many2one(comodel_name="prd.document")
    groups = fields.One2many(comodel_name="prd.rule.groups",inverse_name="rule_id")