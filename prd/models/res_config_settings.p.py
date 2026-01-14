from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError
import logging

_logger = logging.getLogger(__name__)

class ConfSetting(models.TransientModel):
    _inherit = "res.config.settings"

    github_token = fields.Char(
        string="Github Token", store=True, config_parameter='prd.github_token')

    gitlab_token = fields.Char(
        string="GitLab Token", store=True, config_parameter='prd.gitlab_token')
