from odoo import http
from odoo.http import request

class MyModuleController(http.Controller):

    # @http.route('/prd_module/downloadCode/<int:record_id>', type='http', auth='user')
    # def download_code(self, record_id, **kwargs):
    #     record = request.env['prd.document'].browse(record_id)
    #     tar_bytes = record.button_export_module()  # Din metod som skapar zip
    #     filename = 'my_module.tar.gz'
    #     headers = [
    #         ('Content-Type', 'application/gzip'),
    #         ('Content-Disposition', f'attachment; filename="{filename}"'),
    #     ]
    #     return request.make_response(tar_bytes, headers)