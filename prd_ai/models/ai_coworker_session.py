# -*- coding: utf-8 -*-
"""PRD-kontext på ai.coworker.session — domänfält för prd.

prd-ai-coworkers: `prd_id` läggs via arv i bryggan (core förblir
domän-rent — inga prd.*-referenser i ai_agent_core).

Registrerar även resolver-strategin "prd_partner" i core-registret så
coworkers med `cost_context_partner_strategy = "prd_partner"` får
partner härledd från PRD-dokumentet.
"""

import logging
import re

from odoo import fields, models

_logger = logging.getLogger(__name__)


def _prd_partner_strategy(session):
    """Resolver: hitta res.partner via prd.document.

    Prioritet:
    1. prd_id.stakeholder_ids med roll=owner (om fält finns)
    2. prd_id.author_id (dokumentets författare)
    3. prd_id.company_id.partner_id (dokumentets företag)
    """
    if not session.prd_id:
        return
    prd = session.prd_id
    # 1. Primary stakeholder (roll=owner) — om prd.stakeholder har roll-fält
    try:
        if 'stakeholder_ids' in prd._fields:
            for sh in prd.stakeholder_ids:
                role = getattr(sh, 'role', False) or getattr(sh, 'sh_type', False)
                if role and str(role) in ('owner', 'primary'):
                    if sh.partner_id:
                        session.partner_id = sh.partner_id.id
                        return
    except Exception:
        pass
    # 2. Författare (res.users → partner)
    if prd.author_id and prd.author_id.partner_id:
        session.partner_id = prd.author_id.partner_id.id
        return
    # 3. Företag
    if prd.company_id and prd.company_id.partner_id:
        session.partner_id = prd.company_id.partner_id.id


try:
    from odoo.addons.ai_agent_core.models.ai_session import (
        register_cost_context_strategy)
    register_cost_context_strategy('prd_partner', _prd_partner_strategy)
except Exception as e:  # pragma: no cover — modulordning
    _logger.warning('kunde inte registrera prd_partner-strategi: %s', e)


class AICoworkerSessionPRD(models.Model):
    _inherit = 'ai.coworker.session'

    prd_id = fields.Many2one(
        'prd.document', string='PRD', index=True,
        ondelete='set null',
        help='PRD-dokument som sessionen arbetar med. '
             'Sätts via prd-verktyg eller chat-kontext.')

    def _capture_context(self, task=None, project=None, partner=None,
                         prd=None):
        """En enda skrivpunkt för PRD-kontext (D2).

        Härledning: prd_id ← givet dokument. Befintliga värden behålls
        om inget nytt ges ("senast arbetad kontext vinner" — inga
        nollställningar).
        """
        self.ensure_one()
        vals = {}
        if prd:
            p = prd if isinstance(prd, models.BaseModel) else \
                self.env['prd.document'].browse(int(prd))
            if p:
                vals['prd_id'] = p.id
        if vals:
            self.write(vals)
        return self

    def _session_capture_context(self):
        """Core-hook: härled partner via resolver-strategin (prd_ai).

        Anropas av openai_api-vägen när sessionen skapats/återfunnits.
        Självständig (anropar strategin direkt) så den fungerar även om
        coworkerns `cost_context_partner_strategy` inte satts än.
        """
        self.ensure_one()
        try:
            _prd_partner_strategy(self)
        except Exception as e:
            _logger.warning('session capture (prd) failed: %s', e)
        return self

    def _session_auto_capture(self, prompt):
        """Deterministisk kontextfångst ur användarens prompt.

        - `prd <id>` / `dokument <id>` / `#<id>` → prd.document
        - annars: dokumenttitel som förekommer i prompten (contains)

        Fångar bara när prd_id saknas ('senast arbetad kontext vinner').
        Tyst no-op vid fel — hooks får aldrig kasta.
        """
        self.ensure_one()
        try:
            text = (prompt or '').strip()
            if not text:
                return self
            if not self.prd_id:
                m = re.search(
                    r'(?:prd|dokument)\s*#?\s*(\d{1,6})', text, re.I)
                if m:
                    d = self.env['prd.document'].browse(int(m.group(1)))
                    if d.exists():
                        self.write({'prd_id': d.id})
                        return self
                # Fallback: dokumenttitel i prompten
                docs = self.env['prd.document'].search(
                    [('active', 'in', (True, False))], limit=50)
                for d in docs:
                    if d.name and d.name.lower() in text.lower():
                        self.write({'prd_id': d.id})
                        break
        except Exception as e:
            _logger.warning('prd auto-capture failed: %s', e)
        return self
