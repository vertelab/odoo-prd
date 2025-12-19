from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError
import logging

_logger = logging.getLogger(__name__)

class PrdRequirement(models.Model):
    _name = 'prd.requirement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'PRD Requirement'

    @api.depends('function_ids.func_id.name', 'function_ids.state')
    def _compute_function_names(self):
        for record in self:
            formatted_names = []
            for func in record.function_ids:
                name = func.func_id.name or ''
                state = dict(func._fields['state'].selection).get(func.state, '') if func.state else ''
                if name and state:
                    formatted_names.append(f"{name} ({state})")
                elif name:
                    formatted_names.append(name)
            record.function_names = ', '.join(formatted_names)

    active = fields.Boolean(string='Active', default=True)
    category = fields.Many2many(
        comodel_name='prd.requirement_category',
        string='Tags',
        help="Categories"
    )
    code = fields.Char(
        string='Code',
        size=8,trim=True,
        help="Requirement Number, unique ID"
    )
    description = fields.Text(string="Description")
    duration_tracking = fields.Float(string='Duration Tracking')
    function_ids = fields.One2many(comodel_name='prd.requirement.function', inverse_name='req_id')
    function_names = fields.Char(string="Functions", compute='_compute_function_names')
    function_names_ids = fields.Many2many(comodel_name='prd.function',string="Function",compute='_compute_function_names_ids') 
    @api.depends('function_ids.func_id')
    def _compute_function_names_ids(self):
        for record in self:
            record.function_names_ids = record.function_ids.mapped('func_id')

    
    name = fields.Char(string="Name", required=True)
    note = fields.Html(string="Comment")
    object_id = fields.Reference(string='Object', selection=lambda m: [(model.model, model.name) for model in
                                                                                 m.env['ir.model'].sudo().search([])],
                               help="Requirement from this object")
    parent_id = fields.Many2one(comodel_name='prd.requirement',compute="_compute_parent_id",store=True)
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Stake Holder",
        help=""
    )
    prd_id = fields.Many2one(
        'prd.document',
        string='PRD',
        ondelete='cascade',
        required=True
    )
    prd_parent_id = fields.Many2one(related="prd_id.parent_id")
    priority = fields.Selection([
        ('must', 'Must'),
        ('should', 'Should'),
        ('could', 'Could')
    ], string="Priority", default='must')

    req_type = fields.Many2one(comodel_name='prd.requirement_type', string="Type", help="", domain="['|',('prd_id','=',prd_id),('prd_id','=',prd_parent_id)]")
    sequence = fields.Integer(string='Sequence')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ongoing', 'Ongoing'),
        ('done', 'Done')
    ], string="State", default='draft')
    to_check = fields.Boolean()
    user_id = fields.Many2one(comodel_name="res.users",string="Responsible")

    @api.depends("code")
    def _compute_parent_id(self):
        for record in self:
            if record.code:
                code = record.code
                
                parent_code_list = record.code.split(".") if "." in record.code else False  
                parent = ".".join(parent_code_list[:len(parent_code_list) - 1]) if parent_code_list else False
                
                parent_id = record.search([("code", "=", parent),("prd_id", "=", record.prd_id.id)],limit=1)

                if parent_id:
                    record.write({"parent_id": parent_id.id})
            else:
                record.parent_id = False

    def set_state_done(self):
        self.state = "done"

    def action_set_responsible(self):
        _logger.error(f"{self=}")
        return {
            'type': 'ir.actions.act_window',
            'name': 'Set Responsible User',
            'res_model': "prd.requirement.wizard",
            'view_mode': 'form',
            'target': 'new',
            'context': { "default_requirement_ids": self.ids }
        }
        
        
    def get_system_report_data(self,req_ids):
        """Hämtar unika module-funktioner med krav-referenser, sorterat A-Ö"""
        # Hämta alla function med module-typ via req.function_ids
        data = {}
        for req in req_ids:
            for func in [f.func_id for f in req.function_ids if f.func_type.implementation_type == 'module']:
                data[func.name] = {
                    'name': func.name,
                    'description': func.description or '',
                    'requirements': ','.join([r.code for r in func.requirement_ids.mapped('req_id')]),
                    'complexity': dict(func._fields['weight'].selection).get(func.weight, ''), 
                    'time': int(func.weight), 
                }
        # ~ data = sorted(set(data),key=lambda d: d['name'])
        return data        


class PRDRequirementFunction(models.Model):
    _name = 'prd.requirement.function'
    _description = 'PRD Request Function'
    _order = "sequence asc"

    prd_id = fields.Many2one(comodel_name='prd.document', string="", help="", ondelete='cascade', required=True)
    prd_parent_id = fields.Many2one(related="prd_id.parent_id")
    func_id = fields.Many2one(comodel_name='prd.function', string="Function", help="", ondelete='cascade', domain="['|',('prd_id','=',prd_id),('prd_id','=',prd_parent_id)]")
    func_state = fields.Selection(related="func_id.state", string='State')
    func_type = fields.Many2one(comodel_name='prd.function_type', string="Type", related="func_id.func_type")
    req_id = fields.Many2one(comodel_name='prd.requirement', string="", help="", ondelete='cascade')
    req_state = fields.Selection(related="req_id.state", string='State')
    req_type = fields.Many2one(comodel_name='prd.requirement_type', string="Type", related="req_id.req_type")
    sequence = fields.Integer(string='Sequence')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ongoing', 'Ongoing'),
        ('done', 'Done')
    ], string="State", default='draft')

class RequirementType(models.Model):
    _name = 'prd.requirement_type'
    _description = 'Requirement Type'

    name = fields.Char(string='Type', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)
    prd_id = fields.Many2one(comodel_name = "prd.document")
    total = fields.Integer(string='Total',compute="_total")
            
    def _total(self):
        active_model = self.env.context.get('active_model',None)
        active_ids = self.env.context.get('active_ids',[]) 
        tot = {}
        if active_model == 'prd.requirement':
            tot = {req.req_type.id: 0 for req in self.env['prd.requirement'].browse(active_ids) if req.req_type}
            for req in self.env['prd.requirement'].browse(active_ids):
                tot[req.req_type.id] += sum([int(t.weight) for t in req.function_ids.mapped('func_id')])
            for tid in tot.keys():
                self.env['prd.requirement_type'].browse(tid).total = tot[tid]
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            _logger.error(f"{self.env.context=}")
            prd_id = vals.get(self.env.context.get('default_prd_id'))
            vals.update({"prd_id": prd_id})
        return super().create(vals_list)
    
class RequirementCategory(models.Model):
    _name = 'prd.requirement_category'
    _description = 'Requirement Category'

    name = fields.Char(string='Category', required=True)
    active = fields.Boolean(string='Active', default=True)
    prd_id = fields.Many2one(comodel_name = "prd.document")
