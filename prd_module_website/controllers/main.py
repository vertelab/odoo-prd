from odoo import http
from odoo.http import request


class WebsitePRDModuleController(http.Controller):

    @http.route(['/apps', '/apps/page/<int:page>'], type='http', auth="public", website=True, sitemap=True)
    def apps_repo_list(self, page=1, **kwargs):
        Repo = request.env['prd.odoo_repo']
        
        # Get all repositories
        repos = Repo.sudo().search([])
        
        # Build repo data with module counts using the module_ids field
        repo_data = []
        for repo in repos:
            repo_data.append({
                'repo': repo,
                'module_count': len(repo.module_ids),
            })
        
        values = {
            'repos': repo_data,
            'page_name': 'apps',
        }
        
        return request.render('prd_module_website.repo_list', values)

    @http.route(['/apps/<model("prd.odoo_repo"):repo>'], type='http', auth="public", website=True, sitemap=True)
    def apps_module_list(self, repo, **kwargs):
        """List all modules in a repository."""
        # Use the module_ids field from the repo
        modules = repo.sudo().module_ids
        
        # Format repo name: split on '-', skip first part, capitalize rest
        repo_display_name = repo.name
        if '-' in repo.name:
            parts = repo.name.split('-')
            # Skip index 0, capitalize remaining parts
            repo_display_name = ' '.join(part.capitalize() for part in parts[1:])
        
        values = {
            'repo': repo,
            'repo_display_name': repo_display_name,
            'modules': modules,
            'page_name': 'apps',
        }
        
        return request.render('prd_module_website.module_list', values)

    @http.route(['/apps/<model("prd.odoo_repo"):repo>/<model("prd.odoo_module"):module>'], type='http', auth="public", website=True, sitemap=True)
    def apps_module_detail(self, repo, module, **kwargs):
        if module.repo_id != repo:
            return request.redirect('/apps')
        
        # Find all versions of this module (same technical_name, different branches)
        Module = request.env['prd.odoo_module']
        all_versions = Module.sudo().search([
            ('technical_name', '=', module.technical_name),
            ('repo_id', '=', repo.id)
        ])
        
        # Get unique branches
        branches = all_versions.mapped('branch_id').sorted(key=lambda b: b.name)

        values = {
            'repo': repo,
            'module': module,
            'all_versions': all_versions,
            'branches': branches,
            'page_name': 'apps',
        }
        
        return request.render('prd_module_website.module_detail', values)
