import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError

_logger = logging.getLogger(__name__)

class ResUsers(models.Model):
    _inherit = 'res.users'

    sftp_hostname = fields.Char()
    sftp_port = fields.Integer(default=22)
    sftp_username = fields.Char()
    