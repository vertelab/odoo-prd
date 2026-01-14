from odoo import models, api
from odoo.exceptions import UserError
from github import Github, Auth
import base64
import logging
import filetype

_logger = logging.getLogger(__name__)


class GitProviderGitHub(models.Model):
    _name = 'git.provider.github'
    _inherit = 'git.provider.mixin'
    _description = 'GitHub Provider'

    @api.model
    def authenticate(self, token):
        """
        Authenticate with GitHub using personal access token.
        
        Args:
            token (str): GitHub personal access token
            
        Returns:
            Github: Authenticated PyGithub client
        """
        try:
            return Github(auth=Auth.Token(token.strip()))
        except Exception as e:
            _logger.error(f"GitHub authentication failed: {e}")
            raise UserError(f"Failed to authenticate with GitHub: {str(e)}")

    @api.model
    def get_repository(self, client, owner, repo_name):
        """
        Get GitHub repository object.
        
        Args:
            client (Github): Authenticated GitHub client
            owner (str): Repository owner
            repo_name (str): Repository name
            
        Returns:
            Repository: PyGithub Repository object
        """
        try:
            # Handle special case for odoo/odoo repository
            full_name = f"odoo/odoo" if owner == 'odoo' else f"{owner}/{repo_name}"
            repo = client.get_repo(full_name)
            _logger.info(f"Successfully accessed GitHub repository: {full_name}")
            return repo
        except Exception as e:
            _logger.error(f"Failed to get GitHub repository {owner}/{repo_name}: {e}")
            raise UserError(f"Could not access repository {owner}/{repo_name}: {str(e)}")

    @api.model
    def get_branches(self, repository):
        """
        Get list of branches from GitHub repository.
        
        Args:
            repository (Repository): PyGithub Repository object
            
        Returns:
            list: List of branch info dicts
        """
        try:
            branches = []
            for branch in repository.get_branches():
                branches.append({
                    'name': branch.name,
                    'commit': branch.commit.sha,
                    'protected': branch.protected,
                })
            _logger.info(f"Retrieved {len(branches)} branches from GitHub repository")
            return branches
        except Exception as e:
            _logger.error(f"Failed to get branches: {e}")
            raise UserError(f"Could not retrieve branches: {str(e)}")

    @api.model
    def get_contents(self, repository, path, branch):
        """
        Get file or directory contents from GitHub.
        
        Args:
            repository (Repository): PyGithub Repository object
            path (str): Path to file or directory
            branch (str): Branch name
            
        Returns:
            ContentFile or list: Single file or list of files/directories
        """
        try:
            contents = repository.get_contents(path, ref=branch)
            _logger.debug(f"Retrieved contents for path: {path} on branch: {branch}")
            return contents
        except Exception as e:
            _logger.error(f"Failed to get contents for {path} on {branch}: {e}")
            raise UserError(f"Could not get contents of {path}: {str(e)}")

    @api.model
    def normalize_file_object(self, file_object):
        """
        Convert GitHub ContentFile to normalized dict.
        
        Args:
            file_object (ContentFile): GitHub ContentFile object
            
        Returns:
            dict: Normalized file information
        """
        try:
            # Determine MIME type
            mime_type = 'text/plain'
            decoded_content = ''
            
            if file_object.type == 'file':
                # Try to decode content
                try:
                    decoded_content = file_object.decoded_content.decode('utf-8')
                    # Check if it's actually binary
                    mime = filetype.guess(base64.b64decode(file_object.content))
                    if mime:
                        mime_type = mime.mime
                    elif '<svg' in decoded_content:
                        mime_type = 'image/svg+xml'
                except (UnicodeDecodeError, AttributeError):
                    # Binary file
                    mime = filetype.guess(base64.b64decode(file_object.content))
                    mime_type = mime.mime if mime else 'application/octet-stream'
            
            # Extract relative path (remove first directory component for modules)
            path_parts = file_object.path.split('/')
            relative_path = '/'.join(path_parts[1:]) if len(path_parts) > 1 else file_object.path
            
            return {
                'name': file_object.name,
                'path': file_object.path,
                'relative_path': relative_path,
                'type': file_object.type,  # 'file' or 'dir'
                'content': file_object.content if file_object.type == 'file' else None,
                'decoded_content': decoded_content,
                'download_url': file_object.download_url,
                'mime_type': mime_type,
                'size': file_object.size,
                'sha': file_object.sha,
            }
        except Exception as e:
            _logger.error(f"Failed to normalize GitHub file object: {e}")
            raise UserError(f"Error processing file object: {str(e)}")

    @api.model
    def get_file_download_url(self, file_object):
        """
        Get download URL for GitHub file.
        
        Args:
            file_object (ContentFile): GitHub ContentFile object
            
        Returns:
            str: Download URL
        """
        return file_object.download_url

    @api.model
    def supports_recursive_tree(self):
        """
        GitHub supports recursive tree listing via get_git_tree().
        
        Returns:
            bool: False (we use manual recursion for consistency)
        """
        return False
