from odoo import models, api
from odoo.exceptions import UserError
import gitlab
import base64
import logging
import filetype

_logger = logging.getLogger(__name__)


class GitProviderGitLab(models.Model):
    _name = "git.provider.gitlab"
    _inherit = "git.provider.mixin"
    _description = "GitLab Provider"

    @api.model
    def authenticate(self, token):
        """
        Authenticate with GitLab using personal access token.

        Args:
            token (str): GitLab personal access token

        Returns:
            gitlab.Gitlab: Authenticated python-gitlab client
        """
        try:
            gl = gitlab.Gitlab("https://git.vertel.se", private_token=token.strip())
            gl.auth()  # Verify authentication
            return gl
        except Exception as e:
            _logger.error(f"GitLab authentication failed: {e}")
            raise UserError(f"Failed to authenticate with GitLab: {str(e)}")

    @api.model
    def get_repository(self, client, owner, repo_name):
        """
        Get GitLab project object.

        Args:
            client (gitlab.Gitlab): Authenticated GitLab client
            owner (str): Project owner/group
            repo_name (str): Project name

        Returns:
            gitlab.v4.objects.Project: GitLab Project object
        """
        try:
            # GitLab uses project path (owner/repo_name)
            project_path = f"{owner}/{repo_name}"
            project = client.projects.get(project_path)
            _logger.info(f"Successfully accessed GitLab project: {project_path}")
            return project
        except Exception as e:
            _logger.error(f"Failed to get GitLab project {owner}/{repo_name}: {e}")
            raise UserError(f"Could not access project {owner}/{repo_name}: {str(e)}")

    @api.model
    def get_branches(self, repository):
        """
        Get list of branches from GitLab project.

        Args:
            repository (gitlab.v4.objects.Project): GitLab Project object

        Returns:
            list: List of branch info dicts
        """
        try:
            branches = []
            for branch in repository.branches.list(get_all=True):
                branches.append(
                    {
                        "name": branch.name,
                        "commit": branch.commit["id"],
                        "protected": branch.protected,
                    }
                )
            _logger.info(f"Retrieved {len(branches)} branches from GitLab project")
            return branches
        except Exception as e:
            _logger.error(f"Failed to get branches: {e}")
            raise UserError(f"Could not retrieve branches: {str(e)}")

    @api.model
    def get_contents(self, repository, path, branch):
        """
        Get file or directory contents from GitLab.

        Args:
            repository (gitlab.v4.objects.Project): GitLab Project object
            path (str): Path to file or directory
            branch (str): Branch name

        Returns:
            object or list: Single file object or list of tree items
        """
        try:
            # First, try to get it as a file
            try:
                file_obj = repository.files.get(file_path=path, ref=branch)
                # Attach project info for download URL construction
                file_obj._project_web_url = repository.web_url
                file_obj._branch = branch
                return file_obj
            except gitlab.exceptions.GitlabGetError:
                # Not a file, try as directory using repository tree
                tree = repository.repository_tree(
                    path=path, ref=branch, recursive=False, get_all=True
                )
                # Enhance tree items with repository reference for later content fetching
                for item in tree:
                    item["_repository"] = repository
                    item["_branch"] = branch
                return tree
        except Exception as e:
            _logger.error(f"Failed to get contents for {path} on {branch}: {e}")
            raise UserError(f"Could not get contents of {path}: {str(e)}")

    @api.model
    def _fetch_blob_content(self, repository, path, branch):
        """
        Fetch actual file content for a blob.

        Args:
            repository: GitLab Project object
            path (str): File path
            branch (str): Branch name

        Returns:
            ProjectFile: GitLab file object with content
        """
        try:
            file_obj = repository.files.get(file_path=path, ref=branch)
            # Attach project info for download URL construction
            file_obj._project_web_url = repository.web_url
            file_obj._branch = branch
            return file_obj
        except Exception as e:
            _logger.error(f"Failed to fetch blob content for {path}: {e}")
            return None

    @api.model
    def normalize_file_object(self, file_object):
        """
        Convert GitLab file/tree object to normalized dict.

        Args:
            file_object: GitLab file or tree item object

        Returns:
            dict: Normalized file information
        """
        try:
            # Check if it's a file object or tree item
            if hasattr(file_object, "file_path"):
                # It's a ProjectFile object (already has content)
                decoded_content = ""
                mime_type = "text/plain"

                # Decode content
                try:
                    content_bytes = base64.b64decode(file_object.content)
                    decoded_content = content_bytes.decode("utf-8")

                    # Check if it's binary
                    mime = filetype.guess(content_bytes)
                    if mime:
                        mime_type = mime.mime
                    elif "<svg" in decoded_content:
                        mime_type = "image/svg+xml"
                except (UnicodeDecodeError, AttributeError):
                    # Binary file
                    mime = filetype.guess(base64.b64decode(file_object.content))
                    mime_type = mime.mime if mime else "application/octet-stream"

                # Extract relative path
                path_parts = file_object.file_path.split("/")
                relative_path = (
                    "/".join(path_parts[1:])
                    if len(path_parts) > 1
                    else file_object.file_path
                )

                # Construct GitLab raw file URL
                # Format: https://git.vertel.se/project/path/-/raw/branch/file/path
                download_url = ""
                if hasattr(file_object, "_project_web_url") and hasattr(
                    file_object, "_branch"
                ):
                    download_url = f"{file_object._project_web_url}/-/raw/{file_object._branch}/{file_object.file_path}"

                return {
                    "name": file_object.file_name,
                    "path": file_object.file_path,
                    "relative_path": relative_path,
                    "type": "file",
                    "content": file_object.content,
                    "decoded_content": decoded_content,
                    "download_url": download_url,
                    "mime_type": mime_type,
                    "size": file_object.size,
                    "sha": file_object.blob_id,
                }
            else:
                # It's a tree item (from repository_tree)
                # For blobs (files), we need to fetch the actual content
                if file_object["type"] == "blob" and "_repository" in file_object:
                    # Fetch the actual file content
                    _logger.debug(f"Fetching content for blob: {file_object['path']}")
                    file_with_content = self._fetch_blob_content(
                        file_object["_repository"],
                        file_object["path"],
                        file_object["_branch"],
                    )

                    if file_with_content:
                        # Recursively call normalize with the file object that has content
                        return self.normalize_file_object(file_with_content)

                # For trees (directories) or blobs without repository reference, return metadata only
                path_parts = file_object["path"].split("/")
                relative_path = (
                    "/".join(path_parts[1:])
                    if len(path_parts) > 1
                    else file_object["path"]
                )

                return {
                    "name": file_object["name"],
                    "path": file_object["path"],
                    "relative_path": relative_path,
                    "type": file_object["type"],  # 'tree' or 'blob'
                    "content": None,
                    "decoded_content": "",
                    "download_url": "",
                    "mime_type": "text/plain",
                    "size": 0,
                    "sha": file_object.get("id", ""),
                }
        except Exception as e:
            _logger.error(f"Failed to normalize GitLab file object: {e}")
            raise UserError(f"Error processing file object: {str(e)}")

    @api.model
    def get_file_download_url(self, file_object):
        """
        Get download URL for GitLab file.

        Args:
            file_object: GitLab file object

        Returns:
            str: Download URL
        """
        if hasattr(file_object, "attributes"):
            return file_object.attributes.get("url", "")
        return ""

    @api.model
    def supports_recursive_tree(self):
        """
        GitLab supports recursive tree listing.

        Returns:
            bool: True (GitLab has native recursive support)
        """
        return True
