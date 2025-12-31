from odoo import models, fields, api
from odoo.exceptions import UserError

class ConfirmationWizard(models.TransientModel):
    _name = 'confirmation.wizard'
    _description = 'Confirmation Dialog'

    message = fields.Text(string='Message', readonly=True)
    title = fields.Char(string='Title', readonly=True)
    is_validated = fields.Boolean(string='Confirmed', default=False)

    def action_confirm(self):
        """OK-knapp - validera och gå vidare"""
        if not self.is_validated:
            raise UserError("Du måste markera 'OK' för att fortsätta!")
        return self.return_action()

    def action_cancel(self):
        """Avbryt"""
        return {'type': 'ir.actions.act_window_close'}

    def return_action(self):
        """Returnera nästa action (anpassa efter ditt behov)"""
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',  # Eller din nästa action
        }
