import openpyxl
import base64
from io import BytesIO
import re

from datetime import datetime, timedelta 
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError
import logging

_logger = logging.getLogger(__name__)

class ProductRequirementDocument(models.Model):
    _inherit = 'prd.document'
    
    def action_excel_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Load Requirements from Excel',
            'res_model': 'prd.excel.wizard',
            'view_mode': 'form',
            'target': 'new',
            # ~ 'context': {'default_week_template_id': self.env.context["default_week_template_id"]},
        }