from . import models
from . import utils



MODULEFIELDS = [
    "application",
    "author",
    "auto_install",
    "category_id",
    "contributors",
    "description",
    "description_html",
    "icon",
    "icon_flag",
    "icon_image",
    "license",
    "maintainer",
    "name",
    "shortdesc",
    "summary",
    "website",
]


def post_init_hook(env):
    """Populerar prd.module med alla installerade moduler."""
    env["prd.odoo_module"].get_modules()
    # ~ if f == "category_id":
    # ~ f = "app_category_id"

    # ~ modules = env['ir.module.module'].search([])
    # ~ vals_list = []

    # ~ for m in modules:
    # ~ vals = {'module_id': m.id}
    # ~ for f in MODULEFIELDS:
    # ~ val = getattr(m, f, False)

    # ~ # Hantera Many2many/relations korrekt

    # ~ if hasattr(val, '__len__') and not (isinstance(val, str) or isinstance(val, bytes)):
    # ~ print(val)
    # ~ vals[f] = [(6, 0, [x.id for x in val if x.id])]
    # ~ elif f == 'license':
    # ~ licence_id = env['prd.odoo_licence'].search([('name','ilike',val)])
    # ~ vals['licence_id'] = licence_id
    # ~ elif f == "category_id":
    # ~ vals["app_category_id"] = val.id
    # ~ else:
    # ~ vals[f] = val
    # ~ vals_list.append(vals)

    # ~ if vals_list:
    # ~ env['prd.odoo_module'].create(vals_list)
