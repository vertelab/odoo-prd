# -*- coding: utf-8 -*-
"""PRD AI-hjälpmetoder — anropas av ai.tool-kod (prd_ai).

Bridge-standard: verktygskod i ai.tool (data-XML) anropar metoder här
(env['ai.coworker'].prd_*). Inga ai.quest/ai.agent-referenser.
"""

import json
import logging

from odoo import models, _

_logger = logging.getLogger(__name__)


class AICoworkerPRDHelper(models.Model):
    _inherit = 'ai.coworker'

    # ── Läs (read_only) ──────────────────────────────────────────────

    def prd_get(self, prd_id):
        """Hämta PRD-dokument + krav + funktioner (JSON)."""
        doc = self.env['prd.document'].sudo().browse(int(prd_id))
        if not doc.exists():
            return json.dumps({'error': 'PRD %s not found' % prd_id})
        return json.dumps({
            'id': doc.id,
            'name': doc.name,
            'description': doc.description or '',
            'goals': doc.goals or '',
            'user_persona': doc.user_persona or '',
            'use_cases': doc.use_cases or '',
            'success_criteria': doc.success_criteria or '',
            'document_type': doc.document_type or '',
            'state': doc.state or '',
            'requirements': [{
                'id': r.id,
                'code': r.code or '',
                'name': r.name,
                'description': r.description or '',
                'priority': r.priority or '',
                'state': r.state or '',
            } for r in doc.requirement_ids],
            'functions': [{
                'id': f.id,
                'name': f.name,
                'description': f.description or '',
                'state': f.state or '',
            } for f in doc.function_ids],
        }, ensure_ascii=False, default=str)

    def prd_requirement_get(self, req_id):
        """Hämta ett specifikt krav (JSON)."""
        req = self.env['prd.requirement'].sudo().browse(int(req_id))
        if not req.exists():
            return json.dumps({'error': 'Requirement %s not found' % req_id})
        return json.dumps({
            'id': req.id,
            'code': req.code or '',
            'name': req.name,
            'description': req.description or '',
            'priority': req.priority or '',
            'state': req.state or '',
            'prd_id': req.prd_id.id if req.prd_id else None,
            'function_ids': [f.id for f in req.function_ids.mapped('func_id')],
        }, ensure_ascii=False, default=str)

    def prd_stakeholder_get(self, prd_id):
        """Hämta stakeholders för ett PRD-dokument (JSON)."""
        doc = self.env['prd.document'].sudo().browse(int(prd_id))
        if not doc.exists():
            return json.dumps({'error': 'PRD %s not found' % prd_id})
        stakeholders = []
        for sh in doc.stakeholder_ids:
            stakeholders.append({
                'id': sh.id,
                'name': sh.name or '',
                'partner_id': sh.partner_id.id if sh.partner_id else None,
            })
        return json.dumps(stakeholders, ensure_ascii=False, default=str)

    def prd_function_get(self, func_id):
        """Hämta en funktion inkl. odoo_view_ids (JSON)."""
        fn = self.env['prd.function'].sudo().browse(int(func_id))
        if not fn.exists():
            return json.dumps({'error': 'Function %s not found' % func_id})
        views = []
        for vt in fn.odoo_view_ids:
            views.append({
                'id': vt.id,
                'name': vt.name or '',
                'code': vt.code or '',
                'prompt': vt.prompt or '',
            })
        return json.dumps({
            'id': fn.id,
            'name': fn.name,
            'description': fn.description or '',
            'input_data': fn.input_data or '',
            'process_data': fn.process_data or '',
            'output_data': fn.output_data or '',
            'state': fn.state or '',
            'odoo_view_ids': views,
        }, ensure_ascii=False, default=str)

    # ── Skriv (write, HITL-gate) ─────────────────────────────────────

    def prd_requirement_set_status(self, req_id, status):
        """Sätt status på ett krav (draft/ongoing/done)."""
        req = self.env['prd.requirement'].sudo().browse(int(req_id))
        if not req.exists():
            return 'Requirement %s not found' % req_id
        valid = dict(req._fields['state'].selection)
        if status not in valid:
            return 'Invalid status: %s (valid: %s)' % (status, ', '.join(valid))
        req.state = status
        return 'Requirement %s (%s) → %s' % (req_id, req.name, status)

    def prd_module_design(self, prd_id, design_text):
        """Spara en moduldesign som plan på PRD-dokumentet.

        Designen (tekniskt namn, modellista, vyplan, manifest-skiss)
        sparas i dokumentets description (append) så den blir spårbar.
        Ingen prd.odoo_module-skapelse — prd_module utelämnas.
        """
        doc = self.env['prd.document'].sudo().browse(int(prd_id))
        if not doc.exists():
            return 'PRD %s not found' % prd_id
        marker = '## Moduldesign (PRD Module Builder)\n'
        new_block = marker + (design_text or '') + '\n'
        # Ersätt tidigare design-block om det finns, annars appenda
        desc = doc.description or ''
        if marker in desc:
            desc = desc.split(marker)[0] + new_block
        else:
            desc = (desc.rstrip() + '\n\n' + new_block) if desc else new_block
        doc.description = desc
        return 'Moduldesign sparad på PRD %s' % prd_id

    def _capture_session_from_prd(self, prd_id):
        """Tagga den aktuella sessionen med PRD-kontext (prd-ai).

        Sessionen hämtas ur env-kontexten (`_ai_context_model`/
        `_ai_context_id`, satta av openai_api-vägen). Tyst no-op om ingen
        session är aktiv — hooks får aldrig kasta.
        """
        try:
            if self.env.context.get('_ai_context_model') != 'ai.coworker.session':
                return self.env['ai.coworker.session']
            sess = self.env['ai.coworker.session'].browse(
                int(self.env.context.get('_ai_context_id') or 0))
            if not sess.exists():
                return self.env['ai.coworker.session']
            sess._capture_context(object_ref=prd_id)
            return sess
        except Exception as e:
            _logger.warning('session capture from prd failed: %s', e)
            return self.env['ai.coworker.session']
