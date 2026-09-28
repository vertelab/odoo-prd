# -*- coding: utf-8 -*-
"""prd.document — OKF-indexerbar (prd_ai).

VARFÖR: ett PRD-dokument ÄR kunskap — det beskriver vad som ska byggas
och varför. Modellen bär nio Text-fält (description, goals, user_persona,
use_cases, success_criteria, dependencies, risks m.fl.) som tillsammans
är dokumentets hela innehåll, och som ingen söker i idag.

Den generiska kroppskällan fångar dem alla — bryggan behöver inte räkna
upp dem. Lägger prd-modellen till ett fält, följer det med automatiskt.

Modellen äger sina KÄLLOR; `ai.okf.mixin` äger fälten och flaggan.
"""

from odoo import models, fields


class PrdDocument(models.Model):
    _name = 'prd.document'
    _inherit = ['prd.document', 'ai.okf.mixin']

    # OKF-taggar: egen relationstabell (en many2many kan inte ligga
    # pa en abstrakt mixin — den ger samma tabell for alla arvande).
    okf_tags = fields.Many2many(
        'ai.okf.tag', 'prd_document_okf_tag_rel', 'res_id', 'tag_id',
        string='OKF Tags')

    # ── Källor ─────────────────────────────────────────────────────────
    #
    # `okf_body`  generisk: name + description + goals + user_persona +
    #             use_cases + success_criteria + dependencies + risks
    # `okf_links` generisk: `parent_id` (self-relation — ett PRD kan ha
    #             barn-PRD:er), `author_id`/`product_owner_id`/
    #             `approved_by_id` (res.users bär mixinen via base_ai),
    #             `company_id`

    def _okf_artifact_type(self):
        """Bryggans egen typ (okf-mixin D12)."""
        return 'prd_document'

    def _okf_summary_source(self):
        """Dokumentets titel ÄR dess sammanfattning.

        Deterministisk och gratis — ingen LLM behövs för att veta det.
        """
        self.ensure_one()
        return self.name or None

    def _okf_dirty_fields(self):
        """Fält vars ändring gör OKF-fälten inaktuella.

        `version` ingår: en ny version är ett nytt innehåll.
        """
        return {'name', 'description', 'goals', 'user_persona',
                'use_cases', 'success_criteria', 'dependencies', 'risks',
                'version', 'parent_id', 'active'}

    def _okf_skip_reason(self):
        """Arkiverat dokument = "tomt just nu", inte "tomt för alltid"."""
        return None

    # ── Registrering (okf-mixin D11) ───────────────────────────────────

    def _register_hook(self):
        """Registrera modellen för dirty-indexering.

        Registrering, inte överridning: `_okf_indexable_models()` är
        `@api.model` på en abstrakt modell (mätt på luke18 2026-09-22).
        """
        res = super()._register_hook()
        self.env['ai.okf.mixin']._okf_register_indexable('prd.document')
        return res
