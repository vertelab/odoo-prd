from datetime import datetime, timedelta
from github import Github, Auth
from odoo import api, fields, models, modules, tools, _
from odoo.addons.base.models.avatar_mixin import get_hsl_from_seed
from odoo.addons.prd_module.utils import TarFileWriter, SFTPFileWriter
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo.tools.misc import topological_sort, get_flag
from random import randint
from secrets import choice
import base64
import logging
import os
import re
import requests

_logger = logging.getLogger(__name__)

class OdooViewType(models.Model):
    _name = "prd.odoo_view_type"
    _description = "Odoo View Type"

    name = fields.Char(string="View Type Name", required=True)
    code = fields.Char(string="View Type Code", required=True)
    description = fields.Text(string="Description")
    prompt = fields.Text(string="Prompt")
    active = fields.Boolean(string="Active", default=True)
