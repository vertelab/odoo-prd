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
        string='Code', size=6,
        trim=True,
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
    priority = fields.Selection([
        ('must', 'Must'),
        ('should', 'Should'),
        ('could', 'Could')
    ], string="Priority", default='must')
    req_type = fields.Many2one(comodel_name='prd.requirement_type', string="Type", help="")
    sequence = fields.Integer(string='Sequence')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ongoing', 'Ongoing'),
        ('done', 'Done')
    ], string="State", default='draft')
    to_check = fields.Boolean()

    def set_state_done(self):
        self.state = "done"

class PRDRequirementFunction(models.Model):
    _name = 'prd.requirement.function'
    _description = 'PRD Request Function'
    _order = "sequence asc"

    func_id = fields.Many2one(comodel_name='prd.function', string="Function", help="", ondelete='cascade')
    req_id = fields.Many2one(comodel_name='prd.requirement', string="", help="", ondelete='cascade')
    prd_id = fields.Many2one(comodel_name='prd.document', string="", help="", ondelete='cascade')
    func_type = fields.Many2one(comodel_name='prd.function_type', string="Type", help="" , ondelete='cascade')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ongoing', 'Ongoing'),
        ('done', 'Done')
    ], string="State", default='draft')    
    sequence = fields.Integer(string='Sequence')

class RequirementType(models.Model):
    _name = 'prd.requirement_type'
    _description = 'Requirement Type'

    name = fields.Char(string='View Type Name', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)
    
class RequirementCategory(models.Model):
    _name = 'prd.requirement_category'
    _description = 'Requirement Category'

    name = fields.Char(string='Category', required=True)
    active = fields.Boolean(string='Active', default=True)