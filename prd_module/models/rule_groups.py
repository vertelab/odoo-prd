import logging
from datetime import datetime, timedelta 

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError

_logger = logging.getLogger(__name__)

class PrdRuleGroups(models.Model):
    _name = 'prd.rule.groups'
    _description = 'Glue model for prd.rule and res.groups'

    rule_id = fields.Many2one(comodel_name="prd.rule")
    groups_id = fields.Many2one(comodel_name="res.groups")