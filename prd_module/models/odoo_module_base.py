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


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    repo_id = fields.Many2one(comodel_name="prd.odoo_repo", string="Repo", help="")
    technical_name = fields.Char(string="Technical Name")

class OdooModuleMixin(models.AbstractModel):
    _name = "prd.odoo_module.mixin"
    _description = "Odoo Module Mixin"

    active = fields.Boolean(string="Active", default=True)
    app_category_id = fields.Many2one("ir.module.category", string="Category")
    application = fields.Boolean(string="Application")
    auto_install = fields.Boolean(
        "Automatic Installation",
        help="An auto-installable module is automatically installed by the "
        "system when all its dependencies are satisfied. "
        "If the module has no dependency, it is always installed.",
    )
    author = fields.Char("Author")
    contributors = fields.Text("Contributors")
    description = fields.Text(string="Description")
    description_html = fields.Html(string="Index")
    icon = fields.Char(string="Icon URL")
    icon_image = fields.Binary(string="Icon", compute="_get_icon_image")
    banner_image = fields.Binary(string="Banner", compute="_get_icon_image")
    icon_flag = fields.Char(
        string="Flag", compute="_get_icon_image", inverse="_inverse_icon_flag"
    )
    licence_id = fields.Many2one(
        comodel_name="prd.odoo_licence", string="Licence", help=""
    )
    maintainer = fields.Char("Maintainer")
    model_access_ids = fields.One2many(
        comodel_name="prd.model.access", inverse_name="prd_id"
    )
    module_id = fields.Many2one(
        comodel_name="ir.module.module", string="Module", help=""
    )
    repo_id = fields.Many2one(comodel_name="prd.odoo_repo", string="Repo", help="")
    rule_ids = fields.One2many(comodel_name="prd.rule", inverse_name="prd_id")
    summary = fields.Char(string="Summary")
    technical_name = fields.Char(string="Technical Name")
    website = fields.Char(string="Website")
    # ~ url = fields.Char('URL', )
    sequence = fields.Integer("Sequence", default=100)
    # ~ dependency_ids = fields.Many2many(comodel_name='prd.odoo_module',string='_',help="") # relation|column1|column2
    # ~ dependency_ids = fields.One2many(  comodel_name='prd.odoo_module.dependency',
    # ~ inverse_name='module_id',
    # ~ string='Dependencies',)

    # ~ icon_image = fields.Binary(string='Icon', compute='_get_icon_image')
    # ~ banner_image = fields.Binary(string='Banner', compute='_get_icon_image')
    # ~ icon_flag = fields.Char(string='Flag', compute='_get_icon_image',  inverse='_inverse_icon_flag')
    def _get_icon_image(self):
        for module in self:
            icon_image = (
                module.icon_image_file_id.content if module.icon_image_file_id else None
            )
            banner_image = (
                module.banner_image_file_id.content
                if module.icon_image_file_id
                else None
            )
            module.icon_flag = (
                get_flag(
                    (
                        self.module_id.get_module_info(module.name).get(
                            "countries", []
                        )[0]
                        or ""
                    ).upper()
                )
                if len(self.module_id.get_module_info(module.name).get("countries", []))
                == 1
                else ""
            )

    @api.model
    def _module2dict(self, module):
        fields = [
            "app_category_id",
            "application",
            "auto_install",
            "author",
            "contributors",
            "description",
            "description_html",
            "icon",
            "icon_image",
            "licence_id",
            "maintainer",
            "name",
            "summary",
            "technical_name",
            "website",
            "sequience",
            "dependencies_ids",
        ]

        return {
            field_name: module[field_name]
            for field_name in module.fields_get()
            if field_name in fields
        }

    @api.onchange("module_id")
    def _onchange_module_id(self):
        for record in self:
            if record.module_id and record._name == "prd.document":
                for key, value in self._module2dict(record.module_id).items():
                    setattr(record, key, value)
                # ~ d = {field_name: record[field_name] for field_name in record.fields_get()}
                # ~ raise UserError(f"{d}")
            if record.module_id and record._name != "prd.document":
                for key, value in self._module2dict(record.module_id).items():
                    setattr(record, key, value)

    # ~ @api.depends('icon')
    def _get_icon_image(self):
        self.icon_image = ""
        for module in self:
            if not module.id:
                continue
            if module.icon:
                path = os.path.join(module.icon.lstrip("/"))
            else:
                path = modules.module.get_module_icon_path(module)
            if path:
                try:
                    with tools.file_open(
                        path, "rb", filter_ext=(".png", ".svg", ".gif", ".jpeg", ".jpg")
                    ) as image_file:
                        module.icon_image = base64.b64encode(image_file.read())
                except FileNotFoundError:
                    module.icon_image = ""
            countries = self.module_id.get_module_info(module.name).get("countries", [])
            country_code = len(countries) == 1 and countries[0]
            module.banner_image = False
            # ~ module.icon_flag = get_flag(country_code.upper()) if country_code else ''

    def _inverse_icon_flag(self):
        for record in self:
            record.icon_flag = record.icon_flag

            # ~ if record.icon_flag == 'no-icon':
            # ~ record.icon = False
            # ~ record.icon_image = False
            # ~ elif record.icon_flag == 'has-icon-url':
            # ~ record.icon_image = False  # Rensa bild om URL väljs
            # ~ elif record.icon_flag == 'has-icon-image':
            # ~ record.icon = False  # Rensa URL om bild väljs

    def sftp_upload(self):
        return self._sftp_upload_module()

    def _write_module_files(self, writer, file_entries):
        written_paths = []
        for relative_path, content in file_entries:
            clean_path = (relative_path or "").strip().lstrip("/")
            if not clean_path:
                continue

            if "/" in clean_path:
                dir_path, filename = clean_path.rsplit("/", 1)
                dir_path = f"{dir_path}/"
            else:
                dir_path, filename = "", clean_path

            if not filename:
                continue

            written_paths.append(writer.write_file(dir_path, filename, content))

        return written_paths

    def _sftp_upload_module(self):
        self.ensure_one()

        hostname = self.env.user.sftp_hostname
        port = self.env.user.sftp_port
        username = self.env.user.sftp_username

        if not hostname or not port or not username:
            raise UserError(
                f"One of the following values are not set on the user {self.env.user.name}\n\n"
                f"Hostname: {hostname}\nPort: {port}\nUsername: {username}"
            )

        technical_name = self.technical_name or (
            self.module_id.technical_name if self.module_id else self.name
        )

        repo_name = (
            self.repo_id.name
            if self.repo_id
            else (self.module_id.repo_id.name if self.module_id and self.module_id.repo_id else self.name)
        )

        module_path = f"/usr/share/{repo_name}/{technical_name}/"

        writer = None
        try:
            writer = SFTPFileWriter(
                username=username,
                hostname=hostname,
                port=port,
                module_path=module_path,
            )
            self._build_module_structure(writer)

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Success"),
                    "message": _("Module uploaded successfully to %s:%s%s")
                    % (hostname, port, module_path),
                    "type": "success",
                    "sticky": False,
                },
            }
        except Exception as e:
            _logger.error(f"SFTP upload failed: {str(e)}")
            raise UserError(f"Failed to upload module via SFTP:\n\n{str(e)}")
        finally:
            if writer:
                writer.close()


# ~ class PrdDependency(models.Model):
# ~ _name = 'prd.odoo_module.dependency'
# ~ _inherit = "ir.module.module.dependency"
# ~ _description = 'PRD dependencies for modules'

# ~ module_id = fields.Many2one(comodel_name='prd.odoo_module',string="Module",help="")
# ~ dep_module_id = fields.Many2one(comodel_name='prd.odoo_module',string="Depends",help="Module that is a dependency")




class OdooModule(models.Model):
    _name = "prd.odoo_module"
    _inherit = [
        "prd.odoo_module.mixin",
        "mail.thread",
        "mail.activity.mixin",
    ]
    _description = "Odoo Module"

    name = fields.Char(string="Name", required=True)
    branch_id = fields.Many2one(
        comodel_name="prd.odoo_branch", string="Branch", help=""
    )  # TODO Domain repo_id.branch_ids

    @api.model
    def get_modules(self):
        for mod in self.env["ir.module.module"].search([]):
            if self.search([("technical_name", "=", mod.name)], limit=1):
                continue
            vals = self._module2dict(mod)
            vals["technical_name"] = vals["name"]
            vals["name"] = mod.shortdesc
            vals["module_id"] = mod.id
            # ~ vals['dependencies_id'] = [(6, 0, [x.id for x in vals['dependencies_id'] if x._name == 'ir.module.module' and x.id])]
            # ~ if not (hasattr(mod.dependencies_id, '_name') and mod.dependencies_id._name == 'ir.module.module.dependency'):
            # ~ vals['dependencies_id'] = None
            # ~ print(f"DEBUG: type(mod.dependencies_id) = {type(mod.dependencies_id)}") <class 'odoo.api.ir.module.module.dependency'>

            new_mod = self.create(vals)
            # ~ if mod.dependencies_id:
            # ~ new_mod.write({'dependencies_id': [(4, dep.id) for dep in mod.dependencies_id]})

class PrdRule(models.Model):
    _name = "prd.rule"
    _description = "PRD rules for modules"

    prd_id = fields.Many2one(comodel_name="prd.document")
    file_id = fields.Many2one(comodel_name="prd.odoo_module.file", string="Source File")
    
    name = fields.Char(string="Name")
    model_ref = fields.Char(string="Model Ref")
    domain_force = fields.Text(string="Domain")
    groups = fields.Many2many(
        comodel_name="prd.rule.groups",
        string="Groups",
    )
    
    perm_read = fields.Boolean(string="Read", default=True)
    perm_write = fields.Boolean(string="Write", default=True)
    perm_create = fields.Boolean(string="Create", default=True)
    perm_unlink = fields.Boolean(string="Delete", default=True)



class PrdLicence(models.Model):
    _name = "prd.odoo_licence"
    _description = "PRD model licences"

    name = fields.Char(string="Licence")
    code = fields.Char(string='Licence Code', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)


class PrdModelAccess(models.Model):
    _name = "prd.model.access"
    _description = "PRD model to set access rights for modules and models"

    prd_id = fields.Many2one(comodel_name="prd.document")
    file_id = fields.Many2one(comodel_name="prd.odoo_module.file", string="Source File")
    
    name = fields.Char(string="Name")
    model_ref = fields.Char(string="Model Ref")
    group_ref = fields.Char(string="Group Ref")
    
    perm_read = fields.Boolean(string="Read", default=True)
    perm_write = fields.Boolean(string="Write", default=True)
    perm_create = fields.Boolean(string="Create", default=True)
    perm_unlink = fields.Boolean(string="Delete", default=True)


class PrdRuleGroups(models.Model):
    _name = 'prd.rule.groups'
    _description = 'PRD Extracted Groups'

    prd_id = fields.Many2one(comodel_name="prd.document")
    file_id = fields.Many2one(comodel_name="prd.odoo_module.file", string="Source File")
    
    name = fields.Char(string='Group Ref / Ext ID', required=True)
    description = fields.Char(string='Description / Name')