from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class GitProviderMixin(models.AbstractModel):
    """
    Abstract mixin defining the interface for git provider adapters.
    
    All git provider implementations (GitHub, GitLab, etc.) must inherit
    from this mixin and implement all abstract methods.
    """
    _name = 'git.provider.mixin'
    _description = 'Git Provider Mixin'

    @api.model
    def authenticate(self, token):
        """
        Authenticate with the git provider.
        
        Args:
            token (str): Authentication token for the provider
            
        Returns:
            object: Authenticated client object for the provider
            
        Raises:
            UserError: If authentication fails
        """
        raise NotImplementedError("authenticate() must be implemented by provider")

    @api.model
    def get_repository(self, client, owner, repo_name):
        """
        Get repository object from the provider.
        
        Args:
            client (object): Authenticated client from authenticate()
            owner (str): Repository owner/organization
            repo_name (str): Repository name
            
        Returns:
            object: Provider-specific repository object
            
        Raises:
            UserError: If repository not found or access denied
        """
        raise NotImplementedError("get_repository() must be implemented by provider")

    @api.model
    def get_branches(self, repository):
        """
        Get list of branches from repository.
        
        Args:
            repository (object): Repository object from get_repository()
            
        Returns:
            list: List of dicts with branch information:
                [{'name': 'main', 'commit': 'sha123...', ...}, ...]
        """
        raise NotImplementedError("get_branches() must be implemented by provider")

    @api.model
    def get_contents(self, repository, path, branch):
        """
        Get file or directory contents from repository.
        
        Args:
            repository (object): Repository object from get_repository()
            path (str): Path to file or directory
            branch (str): Branch name
            
        Returns:
            object or list: Single file object or list of file/dir objects
        """
        raise NotImplementedError("get_contents() must be implemented by provider")

    @api.model
    def normalize_file_object(self, file_object):
        """
        Convert provider-specific file object to normalized dict format.
        
        This ensures consistent file object structure across all providers.
        
        Args:
            file_object (object): Provider-specific file object
            
        Returns:
            dict: Normalized file information:
                {
                    'name': str,              # File/directory name
                    'path': str,              # Full path in repository
                    'relative_path': str,     # Path relative to module root
                    'type': str,              # 'file' or 'dir'
                    'content': str,           # Base64 encoded content (for files)
                    'decoded_content': str,   # Decoded text content (for text files)
                    'download_url': str,      # URL to download file
                    'mime_type': str,         # MIME type (if available)
                    'size': int,              # File size in bytes
                }
        """
        raise NotImplementedError("normalize_file_object() must be implemented by provider")

    @api.model
    def get_file_download_url(self, file_object):
        """
        Get download URL for a file object.
        
        Args:
            file_object (object): Provider-specific file object
            
        Returns:
            str: URL to download the file
        """
        raise NotImplementedError("get_file_download_url() must be implemented by provider")

    @api.model
    def supports_recursive_tree(self):
        """
        Check if provider supports recursive directory tree listing.
        
        Returns:
            bool: True if provider has native recursive tree support
        """
        return False  # Default: manual recursion required
