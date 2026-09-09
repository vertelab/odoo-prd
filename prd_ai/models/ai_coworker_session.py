# -*- coding: utf-8 -*-
"""Arbetsobjekt-kontext på ai.coworker.session — generisk referens.

prd-ai-coworkers: sessionen kan kopplas till ett "arbetsobjekt" via det
generiska `object_id`-fältet (Reference: modell + id) i stället för ett
domänspecifikt `prd_id`. Core förblir domän-rent.

`object_id` är utbyggbart: fler objekttyper (ärende, offert, …) läggs
till genom att override:a klassmetoden `_ai_object_types()` i en annan
modul. `prd.document` är den första typen.

Kund (partner_id) härleds via `object_id` när projekt/uppgift saknas:
först objektets eget `partner_id`-fält (om det finns), annars
PRD-specifik härledning (stakeholder owner → författare → företag).

Registrerar resolver-strategin "object_partner" i core-registret.
"""

import logging
import re

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


def _object_partner_strategy(session):
    """Resolver: hitta res.partner via sessionens arbetsobjekt.

    Projekt/uppgift har företräde (project_ai hanterar den kedjan via
    task → projekt → kund). Annars, om sessionen har ett `object_id`
    med härledbar partner, sätts partner_id därifrån.

    Prioritet för partnern:
    1. Objektets eget `partner_id`-fält (om modellen har ett)
    2. PRD-specifikt: stakeholder(owner) → författare → företag
    """
    if 'task_id' in session._fields and session.task_id \
            or 'project_id' in session._fields and session.project_id:
        return  # projektkontext vinner
    obj = session.object_id
    if not obj:
        return
    # 1. Objektets eget partner-fält (generiskt, gäller alla modeller)
    if 'partner_id' in obj._fields and obj.partner_id:
        session.partner_id = obj.partner_id.id
        return
    # 2. PRD-specifik härledning
    if obj._name == 'prd.document':
        # 2a. Primary stakeholder (roll=owner) — om prd.stakeholder har roll-fält
        try:
            if 'stakeholder_ids' in obj._fields:
                for sh in obj.stakeholder_ids:
                    role = getattr(sh, 'role', False) or getattr(sh, 'sh_type', False)
                    if role and str(role) in ('owner', 'primary'):
                        if sh.partner_id:
                            session.partner_id = sh.partner_id.id
                            return
        except Exception:
            pass
        # 2b. Författare (res.users → partner)
        if obj.author_id and obj.author_id.partner_id:
            session.partner_id = obj.author_id.partner_id.id
            return
        # 2c. Företag
        if obj.company_id and obj.company_id.partner_id:
            session.partner_id = obj.company_id.partner_id.id


try:
    from odoo.addons.ai_agent_core.models.ai_session import (
        register_cost_context_strategy)
    register_cost_context_strategy('object_partner', _object_partner_strategy)
except Exception as e:  # pragma: no cover — modulordning
    _logger.warning('kunde inte registrera object_partner-strategi: %s', e)


class AICoworkerSessionObject(models.Model):
    _inherit = 'ai.coworker.session'

    @api.model
    def _ai_object_types(self):
        """Modeller som kan vara arbetsobjekt på en session.

        Utökas av andra moduler genom att override:a denna metod och
        lägga till sina (model, label)-tupler. `prd.document` är den
        första typen.
        """
        return [('prd.document', 'PRD')]

    object_id = fields.Reference(
        selection='_ai_object_types',
        string='Arbetsobjekt', index=True,
        help='Generisk referens till det objekt (PRD, ärende, …) som '
             'sessionen arbetar med. Kund härleds via objektets partner '
             'när projekt/uppgift saknas.')

    def _capture_context(self, task=None, project=None, partner=None,
                         object_ref=None, **kwargs):
        """En enda skrivpunkt för arbetsobjekt-kontext.

        Härledning: object_id ← givet objekt (Reference: 'model,id').
        Befintliga värden behålls om inget nytt ges ("senast arbetad
        kontext vinner" — inga nollställningar).

        Anropar super() så övriga bryggor (t.ex. project_ai:s
        task/projekt/kund) samlas i MRO-kedjan.
        """
        self.ensure_one()
        vals = {}
        if object_ref:
            obj = object_ref if isinstance(object_ref, models.BaseModel) \
                else self.env['prd.document'].browse(int(object_ref))
            if obj and 'object_id' in self._fields:
                vals['object_id'] = '%s,%s' % (obj._name, obj.id)
        if vals:
            self.write(vals)
        return super()._capture_context(task=task, project=project,
                                        partner=partner)

    def _session_capture_context(self):
        """Core-hook: härled partner via resolver-strategin.

        Anropas av openai_api-vägen när sessionen skapats/återfunnits.
        Självständig (anropar strategin direkt) så den fungerar även om
        coworkerns `cost_context_partner_strategy` inte satts än.
        """
        self.ensure_one()
        try:
            _object_partner_strategy(self)
        except Exception as e:
            _logger.warning('session capture (object) failed: %s', e)
        return super()._session_capture_context()

    def _session_auto_capture(self, prompt):
        """Deterministisk kontextfångst ur användarens prompt.

        - `prd <id>` / `dokument <id>` / `#<id>` → prd.document
        - annars: dokumenttitel som förekommer i prompten (contains)

        Fångar bara när object_id saknas ('senast arbetad kontext
        vinner'). Tyst no-op vid fel — hooks får aldrig kasta.
        """
        self.ensure_one()
        try:
            text = (prompt or '').strip()
            if not text:
                return super()._session_auto_capture(prompt)
            if not self.object_id:
                m = re.search(
                    r'(?:prd|dokument)\s*#?\s*(\d{1,6})', text, re.I)
                if m:
                    d = self.env['prd.document'].browse(int(m.group(1)))
                    if d.exists():
                        self.write({
                            'object_id': 'prd.document,%s' % d.id})
                        return super()._session_auto_capture(prompt)
                # Fallback: dokumenttitel i prompten
                docs = self.env['prd.document'].search(
                    [('active', 'in', (True, False))], limit=50)
                for d in docs:
                    if d.name and d.name.lower() in text.lower():
                        self.write({
                            'object_id': 'prd.document,%s' % d.id})
                        break
        except Exception as e:
            _logger.warning('object auto-capture failed: %s', e)
        # Låt övriga bryggor (t.ex. project_ai) fånga sin domänkontext.
        return super()._session_auto_capture(prompt)
