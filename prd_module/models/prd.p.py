import logging
import os
import tarfile
import io
import time
import base64
import paramiko
import json
import urllib

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError

_logger = logging.getLogger(__name__)

class ProductRequirementDocument(models.Model):
    _inherit = 'prd.document'
    
    app_module = fields.Many2one(comodel_name="prd.odoo_module",string="App Module",)
    app_project = fields.Many2one(comodel_name='prd.odoo_repo',string="App Project",help="")
    app_tree = fields.Char(string="Branch Tree", default="14.0")
    app_icon = fields.Image(string="Icon")    
    app_url = fields.Char(string="Website", compute="_get_app_url", default="vertel")
    app_banner = fields.Image(string="App Banner")
    app_summary = fields.Char(string="App Summary")
    app_category = fields.Many2one('ir.module.category', string="Category", default=1)
    app_description = fields.Text(string="App Description", default="The module description goes here.")
    app_manifest = fields.Char(string="App Manifest")
    app_license = fields.Char(string="App License", default="LGPL-3")
    # ~ app_index = fields.Html(string="App Index", translate=html_translate, sanitize_attributes=False,sanitize_form=False, default=_default_description)
    app_index = fields.Html(string="App Index", )
    app_depends = fields.Many2many(comodel_name='prd.odoo_module',string='Dependensies',help="") # relation|column1|column2
    model_access_ids = fields.One2many(comodel_name="prd.model.access",inverse_name="prd_id")
    rule_ids = fields.One2many(comodel_name="prd.rule",inverse_name="prd_id")

    @api.depends('app_module','app_project')
    def _get_app_url(self):	 
        pass
        for b in self:
            if b.app_module and b.app_project:
               b.app_url = "https://vertel.se/apps/"+b.app_project.name+"/"+b.app_module.name
            else:
                b.app_url = False

    def button_export_module(self):
        data = []
        models_init = []
        controllers_init = []
        main_init = []

        module_path = f"{self.app_module.name}/"
        tar_file = io.BytesIO()
        with tarfile.open(fileobj=tar_file, mode='w:gz') as tar:
    
            for function in self.function_ids:
                views_dir = ""
                models_dir = ""
                data_dir = ""
                controllers_dir = ""
                if function.has_views and function.views_filename:
                    views_dir = f"{module_path}views/"
                    self.add_file_to_tar(
                        tar,
                        views_dir,
                        function.views_filename,
                        function.views_xml
                        )
                    data.append(f"views/{function.views_filename}")
                if function.has_models and function.models_filename:
                    models_dir = f"{module_path}models/"
                    self.add_file_to_tar(
                        tar,
                        models_dir,
                        function.models_filename,
                        function.models_src
                        )
                    split_filename = function.models_filename.split(".")[0]
                    models_init.append(f"from . import {split_filename}")
                if function.has_data and function.data_filename:
                    data_dir = f"{module_path}data/"
                    self.add_file_to_tar(
                        tar,
                        data_dir,
                        function.data_filename,
                        function.data_xml
                        )
                    data.append(f"data/{function.data_filename}")
                if function.has_controllers and function.controllers_filename:
                    controllers_dir = f"{module_path}controllers/"
                    self.add_file_to_tar(
                        tar,
                        controllers_dir,
                        function.controllers_filename,
                        function.controllers_src
                        )
                    split_filename = function.controllers_filename.split(".")[0]
                    controllers_init.append(f"from . import {split_filename}")
        
            if models_dir:
                content = "\n".join(models_init)
                self.add_file_to_tar(tar,models_dir,"__init__.py",content)
                main_init.append("from . import models")

            if controllers_dir:
                content = "\n".join(controllers_init)
                self.add_file_to_tar(tar,controllers_dir,"__init__.py",content)
                main_init.append("from . import controllers")

            security_dir = f"{module_path}security/"
            self.add_file_to_tar(tar,security_dir,"ir.model.access.csv",self.create_ir_model_access())
            rec_rule = self.add_file_to_tar(tar,security_dir,f"{self.app_module.name}_record_rules.xml",self.create_record_rules())
            rec_rule = "/".join(rec_rule.split("/")[1:])
            data.append(rec_rule)

            main_init_content = "\n".join(main_init)
            self.add_file_to_tar(tar,module_path,"__init__.py",main_init_content)
            self.add_file_to_tar(tar,module_path,"__manifest__.py",self.create_manifest(data))
        
        tar_file.seek(0)
        ir_att_id = self.env["ir.attachment"].create({
            "name": f"{self.name}",
            "type": "binary",
            "datas": base64.b64encode(tar_file.read()),
            "res_model": self._name,
            "res_id": self.id,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model={ir_att_id._name}&id={ir_att_id.id}&filename={ir_att_id.name}&download=true',
            'target': 'self',
        }
        

    def add_file_to_tar(self,tar,dir_path,filename,content):
        arcname = f"{dir_path}{filename}"
        content = content if content else "" 
        data = content.encode('utf-8')  # Encode string to bytes
        fileobj = io.BytesIO(data)       # Create BytesIO stream from bytes
        tarinfo = tarfile.TarInfo(name=arcname)
        tarinfo.size = len(data)
        tarinfo.mtime = time.time()
        tar.addfile(tarinfo, fileobj=fileobj)
        return arcname

    def sftp_upload(self):
        hostname = self.env.user.sftp_hostname
        port = self.env.user.sftp_port
        username = self.env.user.sftp_username

        if not hostname or not port or not username:
            raise UserError(f"One of the following values are not set on the user {self.env.user.name}\n\nHostname: {hostname}\nPort: {port}\nUsername: {username}")

        module_path = f"/usr/share/{self.app_module.name}/"
        data = []
        models_init = []
        controllers_init = []
        main_init = []

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, username=username, port=port)

        # Open SFTP client
        sftp = ssh.open_sftp()

        self.mkdir_safe(sftp,module_path)

        views_dir = ""
        models_dir = ""
        data_dir = ""
        controllers_dir = ""

        for function in self.function_ids:
   
            if function.has_views and function.views_filename:
                views_dir = f"{module_path}views/"
                self.file_write(
                    sftp,
                    views_dir,
                    function.views_filename,
                    function.views_xml,
                    )
                data.append(f"views/{function.views_filename}")
            if function.has_models and function.models_filename:
                models_dir = f"{module_path}models/"
                self.file_write(
                    sftp,
                    models_dir,
                    function.models_filename,
                    function.models_src,
                    )
                split_filename = function.models_filename.split(".")[0]
                models_init.append(f"from . import {split_filename}")
            if function.has_data and function.data_filename:
                data_dir = f"{module_path}data/"
                self.file_write(
                    sftp,
                    data_dir,
                    function.data_filename,
                    function.data_xml,
                    )
                data.append(f"data/{function.data_filename}")
            if function.has_controllers and function.controllers_filename:
                controllers_dir = f"{module_path}controllers/"
                self.file_write(
                    sftp,
                    controllers_dir,
                    function.controllers_filename,
                    function.controllers_src,
                    )
                split_filename = function.controllers_filename.split(".")[0]
                controllers_init.append(f"from . import {split_filename}")

        if models_dir:
            content = "\n".join(models_init)
            self.file_write(sftp,models_dir,"__init__.py",content)
            main_init.append("from . import models")

        if controllers_dir:
            content = "\n".join(controllers_init)
            self.file_write(sftp,controllers_dir,"__init__.py",content)
            main_init.append("from . import controllers")

        security_dir = f"{module_path}security/"
        self.mkdir_safe(sftp,security_dir)
        self.file_write(sftp,security_dir,"ir.model.access.csv",self.create_ir_model_access())
        rec_rule = self.file_write(sftp,security_dir,f"{self.app_module.name}_record_rules.xml",self.create_record_rules())
        rec_rule = "/".join(rec_rule.split("/")[1:])
        data.append(rec_rule)

        main_init_content = "\n".join(main_init)
        self.file_write(sftp,module_path,"__init__.py",main_init_content)
        
        self.file_write(sftp,module_path,"__manifest__.py",self.create_manifest(data))

    def file_write(self,sftp,path,filename,content):
        self.mkdir_safe(sftp,path)
        file_path = f"{path}{filename}"
        with sftp.file(file_path, 'w+') as remote_file:
            remote_file.write(content if content else "")
            remote_file.close()
        return file_path

    def mkdir_safe(self,sftp,dir,mode=0o775):
        try:
            sftp.mkdir(dir,mode)
        except IOError as e:
            _logger.warning(f"Got this error {e} when making directory with sftp on remote host.\nIt is likely that the directory already exists, will skip creating it.")
                

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
                _logger.warning("--------->> module_url: %s" % module_url )
                _logger.warning("--------->> raw_module_url: %s" % raw_module_url )

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
                        main_screenshot = [image for image in manifest_images if image.endswith('_screenshot.png' or 'banner.png')]
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
            ext_model = f"{first_module}.{rule.model_id.model.replace(".","_")}"
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

    def create_groups_string(self,rule):
        if not rule.groups:
            return ""
        group_string = "["
        for group in rule.groups:
            ext_group_id = self.env["ir.model.data"].search([("model", "=", group.groups_id._name),("res_id", "=", group.groups_id.id)],limit=1)
            group_string += f'(4, ref("{ext_group_id.complete_name}")),'
        group_string += "]"
        return group_string

    def create_ir_model_access(self):
        content = "id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink"
        for access in self.model_access_ids:
            ext_group_id = self.env["ir.model.data"].search([("model", "=", access.group_id._name),("res_id", "=", access.group_id.id)],limit=1)
            first_module = access.model_id.modules.split(",")[0]
            content += f"\naccess_{access.name},{access.name},{first_module}.model_{access.model_id.model.replace(".","_")},{ext_group_id.complete_name},{int(access.perm_read)},{int(access.perm_write)},{int(access.perm_create)},{int(access.perm_unlink)}"
        return content

    def create_manifest(self,data=[]):
        manifest_vals = {
            'name': self.name,
            'version': '1.0',
            'category': self.app_category.name,
            'website': 'https://vertel.se/apps/project/module',
            'summary': self.app_summary,
            'author': 'Vertel AB',
            'license': self.app_license,
            'description': self.app_description,
            'depends': [d.strip() for d in self.dependencies.split(",")] if self.dependencies else [],
            'data': data,
            'installable': True,
            'application': True,
            'qweb': []
        }
        json_str = json.dumps(manifest_vals, indent=2)
        return json_str

        # user_encode_data = json.dumps(manifest_vals, indent=2).encode('utf-8')
        # temp = tempfile.NamedTemporaryFile(mode='w+b')
        # temp.write(user_encode_data)
        # temp.seek(0)
        # attachment_id = self.env['ir.attachment'].create({
        #     'name': '__manifest__.py',
        #     'res_name': self.name,
        #     'res_model': self._name,
        #     'res_id': self.id,
        #     'datas': base64.encodebytes(temp.read()),
        # })
        # temp.close()

        # return {
        #     'type': 'ir.actions.act_window',
        #     'res_model': 'ir.attachment',
        #     'view_type': 'form',
        #     'view_mode': 'form',
        #     'view_id': self.env.ref('website_blog_app.download_manifest_wizard').id,
        #     'res_id': attachment_id.id,
        #     'target': 'new',
        #     'flags': {'mode': 'readonly'},
        # }
