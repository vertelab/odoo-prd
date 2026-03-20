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


class OdooBranch(models.Model):
    _name = "prd.odoo_branch"
    _description = "Odoo Branch"

    name = fields.Char(string="Name", required=True)
    active = fields.Boolean(string='Active', default=True)


class OdooRepo(models.Model):
    _name = "prd.odoo_repo"
    _description = "Odoo Repository"

    name = fields.Char(string="Name", required=True)
    url = fields.Char(string='URL', help='url eg "https://api.github.com/repos/{self.owner}/{self.name}/git/trees/{branch_id.name}?recursive=1"')
    path = fields.Char(string="Path", help="Filesystem path")
    active = fields.Boolean(string='Active', default=True)
    description = fields.Text(string="Description")

    
    module_ids = fields.One2many(
        comodel_name="prd.odoo_module",
        inverse_name="repo_id",
        string="Modules",
        help="",
    )
    owner = fields.Char(
        string="Owner",
        size=64,
        trim=True,
    )
    repo_source = fields.Selection(
        selection=[("github", "Github"), ("gitlab", "Gitlab")], string="Source"
    )
    branch_ids = fields.Many2many(
        comodel_name="prd.odoo_branch", string="Branch", help=""
    )

    @api.onchange("repo_source", "name", "owner")
    def _repo_source(self):
        """Validate repo source selection."""
        if self.repo_source and self.repo_source not in ["github", "gitlab"]:
            raise UserError(f"Unsupported repository source: {self.repo_source}")

    def _get_provider_adapter(self):
        """Factory method to get the appropriate git provider adapter."""
        if not self.repo_source:
            raise UserError(
                "Repository source not configured. Please select GitHub or GitLab."
            )

        if self.repo_source == "github":
            return self.env["git.provider.github"]
        elif self.repo_source == "gitlab":
            return self.env["git.provider.gitlab"]
        else:
            raise UserError(f"Unsupported repository source: {self.repo_source}")

    def _get_auth_token(self):
        """Get authentication token for the configured provider."""
        if not self.repo_source:
            raise UserError("Repository source not configured")

        param_name = f"prd.{self.repo_source}_token"
        authToken = self.env["ir.config_parameter"].sudo().get_param(param_name)

        if not authToken:
            raise UserError(
                f"{self.repo_source.title()} token missing. "
                f"Please configure '{param_name}' in Settings > Technical > Parameters > System Parameters."
            )
        return authToken

    def git_odoo_branches(self):
        """Fetch branches from git repository using configured provider."""
        adapter = self._get_provider_adapter()
        token = self._get_auth_token()

        try:
            client = adapter.authenticate(token)
            repo = adapter.get_repository(client, self.owner, self.name)
            branches = adapter.get_branches(repo)

            # Filter for Odoo version branches (e.g., "14.0", "15.0")
            odoo_branches = [b for b in branches if re.match(r"^\d+\.0$", b["name"])]

            branch_ids = []
            for branch_info in sorted(odoo_branches, key=lambda x: float(x["name"])):
                b = self.env["prd.odoo_branch"].search(
                    [("name", "=", branch_info["name"])], limit=1
                )
                if not b:
                    b = self.env["prd.odoo_branch"].create(
                        {"name": branch_info["name"]}
                    )
                branch_ids.append(b.id)

            if branch_ids:
                self.branch_ids = [(6, 0, branch_ids)]

            _logger.info(
                f"Fetched {len(branch_ids)} Odoo branches from {self.repo_source}"
            )

        except Exception as e:
            _logger.error(f"Failed to fetch branches from {self.repo_source}: {e}")
            raise UserError(f"Could not fetch branches: {str(e)}")

    def _git_repo(self):
        """Get repository object using configured provider."""
        adapter = self._get_provider_adapter()
        token = self._get_auth_token()

        try:
            client = adapter.authenticate(token)
            return adapter.get_repository(client, self.owner, self.name)
        except Exception as e:
            _logger.error(f"Failed to access repository {self.owner}/{self.name}: {e}")
            raise UserError(f"Could not access repository: {str(e)}")

    def get_files(self, filename, branch="14.0"):
        """Get all files in a directory recursively."""
        adapter = self._get_provider_adapter()
        repo = self._git_repo()
        mfiles = []

        if self.owner == "odoo":
            filename = f"addons/{filename}"

        try:
            files = adapter.get_contents(repo, filename, branch)
            if not isinstance(files, list):
                files = [files]
            _logger.info(f"Retrieved {len(files)} items from {filename}")
        except Exception as e:
            _logger.error(f"Could not read {filename=} {branch=}: {e}")
            raise

        # Process files recursively
        while files:
            file_obj = files.pop(0)
            file_info = adapter.normalize_file_object(file_obj)

            pos = 1 if self.owner != "odoo" else 2
            path_parts = file_info["path"].split("/")

            # Skip i18n directories
            if file_info["type"] in ["dir", "tree"]:
                if len(path_parts) > pos and path_parts[pos] == "i18n":
                    continue
                # Get contents of subdirectory
                try:
                    subfiles = adapter.get_contents(repo, file_info["path"], branch)
                    if isinstance(subfiles, list):
                        files.extend(subfiles)
                except Exception as e:
                    _logger.warning(
                        f"Could not read subdirectory {file_info['path']}: {e}"
                    )
            elif file_info["name"] not in [".gitignore"]:
                mfiles.append(file_obj)

        # Filter out .p.py and .p.xml duplicates
        normalized_files = [adapter.normalize_file_object(f) for f in mfiles]
        p_files = set(
            [
                f["path"].replace(".p.", ".")
                for f in normalized_files
                if ".p." in f["path"]
                and (f["path"].endswith(".p.py") or f["path"].endswith(".p.xml"))
            ]
        )

        result = [
            f
            for f, norm in zip(mfiles, normalized_files)
            if norm["path"] not in p_files
        ]

        _logger.info(f"Returning {len(result)} files after filtering")
        return result

    def get_contents(self, filename, branch):
        """Get contents of a file or directory."""
        adapter = self._get_provider_adapter()
        repo = self._git_repo()

        try:
            return adapter.get_contents(repo, filename, branch)
        except Exception as e:
            _logger.error(f"Error getting contents of {filename}: {e}")
            return f"{filename} Error {e}"

    def get_file_content(self, filename, branch):
        """Get decoded content of a file."""
        adapter = self._get_provider_adapter()
        repo = self._git_repo()

        _logger.debug(f"Getting file content: {filename=} {branch=}")
        try:
            file_obj = adapter.get_contents(repo, filename, branch)
            if isinstance(file_obj, list):
                file_obj = file_obj[0]

            file_info = adapter.normalize_file_object(file_obj)
            return file_info["decoded_content"]
        except Exception as e:
            _logger.error(f"Error getting file content {filename}: {e}")
            return f"{filename} Error {e}"



class OdooLibrary(models.Model):
    _name = 'prd.odoo_library'
    _description = 'Odoo Library'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)

   
class OdooModels(models.Model):
    _name = 'prd.odoo_models'
    _description = 'Odoo Models'

    name = fields.Char(string='Name', required=True)
    active = fields.Boolean(string='Active', default=True)
