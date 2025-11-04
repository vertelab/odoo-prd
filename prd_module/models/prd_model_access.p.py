import logging
from datetime import datetime, timedelta 

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError

_logger = logging.getLogger(__name__)

class PrdModelAccess(models.Model):
    _name = 'prd.model.access'
    _inherit = "ir.model.access"
    _description = 'PRD model to set access rights for modules and models'

    prd_id = fields.Many2one(comodel_name="prd.document")