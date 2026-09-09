# -*- coding: utf-8 -*-
"""Tester för prd_ai — session-kontext, resolver, coworkers (prd-ai-coworkers).

Körs med: odoo --test-enable -u prd_ai (eller checkmodule -t).
"""

from odoo.tests import common, tagged


@tagged('post_install', '-at_install')
class TestPRDContext(common.TransactionCase):
    """6.1: object_id på session + resolver object_partner."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'PRD Kund'})
        cls.author = cls.env['res.users'].create({
            'name': 'PRD Författare',
            'login': 'prd_author_%s' % cls.env['res.users'].search_count([]),
            'password': 'test-pass',
        })
        cls.prd = cls.env['prd.document'].create({
            'name': 'Test-PRD',
            'description': 'Testdokument',
            'author_id': cls.author.id,
        })
        cls.coworker = cls.env['ai.coworker'].create({
            'name': 'Test PRD',
            'status': 'active',
            'cost_context_partner_strategy': 'object_partner',
        })

    def _session(self, **kw):
        return self.env['ai.coworker.session'].create(
            dict({'coworker_id': self.coworker.id, 'status': 'active'}, **kw))

    def test_capture_sets_object_id(self):
        """6.1a: _capture_context(object_ref=...) sätter object_id."""
        sess = self._session()
        sess._capture_context(object_ref=self.prd)
        self.assertEqual(sess.object_id, self.prd)

    def test_capture_from_prd_via_context(self):
        """6.1b: _capture_session_from_prd via env-kontext."""
        sess = self._session()
        with self.env.context(_ai_context_model='ai.coworker.session',
                              _ai_context_id=sess.id):
            self.coworker._capture_session_from_prd(self.prd.id)
        self.assertEqual(sess.object_id, self.prd)

    def test_resolver_object_partner_author(self):
        """6.1c: resolver härleder partner från författare."""
        sess = self._session(object_id='prd.document,%s' % self.prd.id)
        sess._session_capture_context()
        self.assertEqual(sess.partner_id, self.author.partner_id)

    def test_auto_capture_from_prompt(self):
        """6.1d: 'prd <id>' i prompten fångas automatiskt."""
        sess = self._session()
        sess._session_auto_capture('prd %d — analysera' % self.prd.id)
        self.assertEqual(sess.object_id, self.prd)


@tagged('post_install', '-at_install')
class TestPRDTools(common.TransactionCase):
    """6.2: verktyg — statusändring kräver HITL-gate via risk_level."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.prd = cls.env['prd.document'].create({
            'name': 'Tool-PRD',
        })
        cls.req = cls.env['prd.requirement'].create({
            'name': 'Krav 1',
            'description': 'Kravbeskrivning',
            'prd_id': cls.prd.id,
        })
        cls.coworker = cls.env['ai.coworker'].create({
            'name': 'Test PRD Tools',
            'status': 'active',
        })

    def test_requirement_set_status(self):
        """6.2a: prd_requirement_set_status uppdaterar status."""
        result = self.coworker.prd_requirement_set_status(self.req.id, 'ongoing')
        self.assertIn('ongoing', result)
        self.assertEqual(self.req.state, 'ongoing')

    def test_requirement_set_status_invalid(self):
        """6.2b: ogiltig status avvisas."""
        result = self.coworker.prd_requirement_set_status(self.req.id, 'bogus')
        self.assertIn('Invalid status', result)

    def test_risk_level_write_gate(self):
        """6.2c: prd_requirement_set_status har risk_level=write (HITL)."""
        tool = self.env['ai.tool'].search(
            [('name', '=', 'prd_requirement_set_status')], limit=1)
        self.assertTrue(tool.exists())
        self.assertEqual(tool.risk_level, 'write')

    def test_prd_get_returns_json(self):
        """6.2d: prd_get returnerar JSON med dokument + krav."""
        import json
        result = json.loads(self.coworker.prd_get(self.prd.id))
        self.assertEqual(result['name'], 'Tool-PRD')
        self.assertEqual(len(result['requirements']), 1)


@tagged('post_install', '-at_install')
class TestPRDCoworkers(common.TransactionCase):
    """6.3: coworkers finns med rätt verktyg/skills."""

    def test_analyst_exists(self):
        """PRD Analyst finns med rätt verktyg + skill."""
        cw = self.env['ai.coworker'].search(
            [('name', '=', 'PRD Analyst')], limit=1)
        self.assertTrue(cw.exists())
        names = cw.tool_ids.mapped('name')
        self.assertIn('prd_get', names)
        self.assertIn('prd_requirement_set_status', names)
        self.assertIn('prd_requirement_get', names)
        skill_names = cw.skill_ids.mapped('name')
        self.assertTrue(any('PRD-analys' in s for s in skill_names))

    def test_module_builder_exists(self):
        """PRD Module Builder finns med rätt verktyg + skill."""
        cw = self.env['ai.coworker'].search(
            [('name', '=', 'PRD Module Builder')], limit=1)
        self.assertTrue(cw.exists())
        names = cw.tool_ids.mapped('name')
        self.assertIn('prd_get', names)
        self.assertIn('prd_function_get', names)
        self.assertIn('prd_module_design', names)
        skill_names = cw.skill_ids.mapped('name')
        self.assertTrue(any('Odoo-moduldesign' in s for s in skill_names))

    def test_openai_init_enabled(self):
        """Båda coworkers har openai_api-init aktiverad."""
        for name in ('PRD Analyst', 'PRD Module Builder'):
            cw = self.env['ai.coworker'].search(
                [('name', '=', name)], limit=1)
            oai = cw.init_type_ids.filtered(
                lambda it: it.init_type == 'openai_api' and it.enabled)
            self.assertTrue(oai, '%s saknar openai_api-init' % name)
