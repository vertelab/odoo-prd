import re
import json
import urllib
import ast
import logging
import traceback
import os
import tarfile
import io
import base64
import time


from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError

from odoo.addons.prd_module.utils import TarFileWriter, SFTPFileWriter # pyright: ignore[reportMissingImports]

_logger = logging.getLogger(__name__)


class ProductRequirementDocument(models.Model):

    _name = "prd.document"
    _inherit = ['prd.document','prd.odoo_module.mixin']


    def action_redirect_to_url(self):
        url = f"/prd_module/download_code/{self.id}"
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "self",
        }

    # def sftp_upload(self):
    #     hostname = self.env.user.sftp_hostname
    #     port = self.env.user.sftp_port
    #     username = self.env.user.sftp_username
    #
    #     if not hostname or not port or not username:
    #         raise UserError(f"One of the following values are not set on the user {self.env.user.name}\n\nHostname: {hostname}\nPort: {port}\nUsername: {username}")
    #
    #     module_path = f"/usr/share/{self.repo_id.name}/"



    def _build_module_structure(self, writer):
        data = []
        models_init = []
        controllers_init = []
        main_init = []

        # Process all functions
        for function in self.function_ids:
            if function.has_views and function.views_filename:
                writer.write_file("views/", function.views_filename, function.views_xml)
                data.append(f"views/{function.views_filename}")

            if function.has_models and function.models_filename:
                writer.write_file("models/", function.models_filename, function.models_src)
                split_filename = function.models_filename.split(".")[0]
                models_init.append(f"from . import {split_filename}")

            if function.has_data and function.data_filename:
                writer.write_file("data/", function.data_filename, function.data_xml)
                data.append(f"data/{function.data_filename}")

            if function.has_controllers and function.controllers_filename:
                writer.write_file("controllers/", function.controllers_filename, function.controllers_src)
                split_filename = function.controllers_filename.split(".")[0]
                controllers_init.append(f"from . import {split_filename}")

        # Create __init__.py files for models
        if models_init:
            content = "\n".join(models_init)
            writer.write_file("models/", "__init__.py", content)
            main_init.append("from . import models")

        # Create __init__.py files for controllers
        if controllers_init:
            content = "\n".join(controllers_init)
            writer.write_file("controllers/", "__init__.py", content)
            main_init.append("from . import controllers")

        # Create security files
        writer.write_file("security/", "ir.model.access.csv", self.create_ir_model_access())

        rec_rule_path = writer.write_file(
            "security/",
            f"{self.name}_record_rules.xml",
            self.create_record_rules()
        )
        # Extract relative path for manifest (remove module path prefix)
        rec_rule_relative = "/".join(rec_rule_path.split("/")[1:])
        data.append(rec_rule_relative)

        # Create main __init__.py
        main_init_content = "\n".join(main_init)
        writer.write_file("", "__init__.py", main_init_content)

        # Create manifest
        writer.write_file("", "__manifest__.py", self.create_manifest(data))

        return data

    def button_export_module(self):
        """Export module as a downloadable tar.gz file"""
        module_path = f"{self.name}/"

        writer = TarFileWriter(module_path)
        self._build_module_structure(writer)

        writer.close()

        tar_file = writer.tar_file
        tar_file.seek(0)
        tar_data = tar_file.read()

        ir_att_id = self.env["ir.attachment"].create({
            "name": f"{self.name}.tar.gz",
            "type": "binary",
            "datas": base64.b64encode(tar_data),
            "res_model": self._name,
            "res_id": self.id,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model={ir_att_id._name}&id={ir_att_id.id}&filename={ir_att_id.name}&download=true',
            'target': 'self',
        }

    def sftp_upload(self):
        """Upload module directly to server via SFTP"""
        hostname = self.env.user.sftp_hostname
        port = self.env.user.sftp_port
        username = self.env.user.sftp_username

        if not hostname or not port or not username:
            raise UserError(
                f"One of the following values are not set on the user {self.env.user.name}\n\n"
                f"Hostname: {hostname}\nPort: {port}\nUsername: {username}"
            )

        if self.app_module.repo_id:
            module_path = f"/usr/share/{self.app_module.repo_id.name}/{self.app_module.technical_name}/"
        else:
            module_path = f"/usr/share/{self.name}/{self.app_module.technical_name}/"

        try:
            writer = SFTPFileWriter(
                username=username,
                hostname=hostname,
                port=port,
                module_path=module_path
            )
            self._build_module_structure(writer)
            writer.close()

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Module uploaded successfully to %s:%s%s') % (hostname, port, module_path),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f"SFTP upload failed: {str(e)}")
            raise UserError(f"Failed to upload module via SFTP:\n\n{str(e)}")


    def sync_module(self):
        git_url = self.env['ir.config_parameter'].sudo().get_param('GitHubBaseUrl')
        raw_git_url = self.env['ir.config_parameter'].sudo().get_param('RawGitHubBaseUrl')

        if not raw_git_url:
            raise UserError(_("Raw Git URL is not set"))
        if not git_url:
            raise UserError(_("Git URL is not set"))
        if not self.app_project:
            raise UserError(_("No Git Project was specified"))
        if not self.app_module:
            raise UserError(_("No Module was specified"))
        for module in self:
            if not module.app_project:
                raise UserError(_("No Git Project was specified %s" % module.name))
            if not module.app_module:
                raise UserError(_("No Module was specified %s" % module.name))
            if not module.app_tree:
                raise UserError(_("No Module Tree was specified %s" % module.name))
            if module.app_project and module.app_module:
                module_url = f"{git_url}/{module.app_project}/tree/{module.app_tree}/{module.app_module}"
                raw_module_url = f"{raw_git_url}/{module.app_project}/{module.app_tree}/{module.app_module}"
                # get icon
                _logger.warning("--------->> module_url: %s" % module_url)
                _logger.warning("--------->> raw_module_url: %s" % raw_module_url)

                icon_data, icon_name = module._wget_sync(f"{raw_module_url}/static/description/icon.png")
                if icon_data and icon_name:
                    module.app_icon = module._create_attachment(icon_data, icon_name)
                # get banner
                manifest_obj = urllib.request.urlopen(f"{raw_module_url}/__manifest__.py").read().decode('utf-8')
                manifest = re.sub(r'(?m)^ *#.*\n?', '', manifest_obj)
                if manifest:
                    manifest = ast.literal_eval(manifest)
                    manifest_images = manifest.get('images')
                    if manifest_images:
                        main_screenshot = [image for image in manifest_images if
                                           image.endswith('_screenshot.png' or 'banner.png')]
                        banner_data, banner_name = self._wget_sync(
                            f"{raw_module_url}{main_screenshot[0] if main_screenshot else manifest_images[0]}"
                        )
                        if banner_data and banner_name:
                            module.app_banner = module._create_attachment(banner_data, banner_name)

                # manifest file
                module._sync_manifest(f"{raw_module_url}/__manifest__.py")

    def _sync_manifest(self, manifest_url):
        try:
            manifest_obj = urllib.request.urlopen(manifest_url).read().decode('utf-8')
            manifest = re.sub(r'(?m)^ *#.*\n?', '', manifest_obj)
            if manifest:
                manifest = ast.literal_eval(manifest)
                self.app_license = manifest.get('license')
                self.app_summary = manifest.get('summary')
        except Exception as e:
            _logger.warning("".join(traceback.format_exc()))
            return None, None

    def _wget_sync(self, url):
        _logger.warning(f"{url=}")
        try:
            file_obj = urllib.request.urlopen(url)
            _logger.warning(f"{file_obj=}")
            file_name = os.path.basename(url)
            _logger.warning(f"{file_name=}")
            return file_obj, file_name
        except Exception as e:
            _logger.warning("".join(traceback.format_exc()))
            return None, None

    def _create_attachment(self, datas, name):
        return base64.encodebytes(datas.read())

    def create_record_rules(self):
        content = "<odoo>\n"
        for rule in self.rule_ids:
            group_string = self.create_groups_string(rule)
            first_module = rule.model_id.modules.split(",")[0]
            ext_model = f"{first_module}.{rule.model_id.model.replace(".", "_")}"
            content += f"\
    <record id='{rule.name}_record_rule' model='ir.rule'>\n \
        <field name='name'>{rule.name}</field>\n \
        <field name='model_id' ref='{ext_model}'/>\n \
        <field name='domain_force'>{rule.domain_force}</field>\n \
        <field name='groups' eval='{group_string}'/>\n \
        <field name='perm_read' eval='{int(rule.perm_create)}'/>\n \
        <field name='perm_write' eval='{int(rule.perm_write)}'/>\n \
        <field name='perm_create' eval='{int(rule.perm_create)}'/>\n \
        <field name='perm_unlink' eval='{int(rule.perm_unlink)}'/>\n \
    </record>\n"
        content += "</odoo>"
        return content

    def create_groups_string(self, rule):
        if not rule.groups:
            return ""
        group_string = "["
        for group in rule.groups:
            ext_group_id = self.env["ir.model.data"].search([
                ("model", "=", group.groups_id._name), ("res_id", "=", group.groups_id.id)
            ], limit=1)
            group_string += f'(4, ref("{ext_group_id.complete_name}")),'
        group_string += "]"
        return group_string

    def create_ir_model_access(self):
        content = "id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink"
        for access in self.model_access_ids:
            ext_group_id = self.env["ir.model.data"].search([
                ("model", "=", access.group_id._name), ("res_id", "=", access.group_id.id)
            ], limit=1)
            first_module = access.model_id.modules.split(",")[0]
            content += (
                f"\naccess_{access.name},{access.name},"
                f"{first_module}.model_{access.model_id.model.replace('.', '_')},"
                f"{ext_group_id.complete_name},"
                f"{int(access.perm_read)},{int(access.perm_write)},"
                f"{int(access.perm_create)},{int(access.perm_unlink)}"
            )
        return content

    def create_manifest(self,data):
        manifest_vals = {
            'name': self.name,
            # 'version': f"{self.major_version}.{self.minor_version}",
            'version': f"{self.version}",
            'category': self.app_category_id.name,
            'website': self.website,
            'summary': self.summary,
            'author': self.env.company.name,
            'license': self.licence_id.name,
            'description': self.description,
            # ~ 'depends': [d.strip() for d in self.dependencies.split(",")] if self.dependencies else [],
            'data': data,
            'installable': True,
            'application': True,
            'qweb': []
        }
        return json.dumps(manifest_vals, indent=2)
