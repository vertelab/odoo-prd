"""Tests for PRD core models: prd.document, prd.requirement, prd.function,
prd.stakeholder, prd.template, and prd.traceability."""

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError
from datetime import date


@tagged("post_install", "-at_install", "prd")
class TestPrdDocument(TransactionCase):
    """Test PRD document creation, state transitions, and computations."""

    def setUp(self):
        super().setUp()
        self.Prd = self.env["prd.document"]
        self.Req = self.env["prd.requirement"]
        self.Func = self.env["prd.function"]
        self.Stakeholder = self.env["prd.stakeholder"]
        self.Template = self.env["prd.template"]
        self.Traceability = self.env["prd.traceability"]

    def test_create_prd(self):
        """PRD should be created with default values."""
        prd = self.Prd.create({
            "name": "Test PRD",
            "description": "A test PRD for unit testing.",
            "document_type": "module",
        })
        self.assertEqual(prd.state, "draft")
        self.assertEqual(prd.version, "1.0")
        self.assertTrue(prd.active)

    def test_state_transitions(self):
        """PRD should transition through states correctly."""
        prd = self.Prd.create({"name": "Test PRD"})

        # draft -> in_review
        prd.action_submit_review()
        self.assertEqual(prd.state, "in_review")

        # in_review -> approved
        prd.action_approve()
        self.assertEqual(prd.state, "approved")
        self.assertTrue(prd.date)

        # approved -> implemented
        prd.action_mark_implemented()
        self.assertEqual(prd.state, "implemented")

        # implemented -> verified
        prd.action_mark_verified()
        self.assertEqual(prd.state, "verified")

    def test_reject(self):
        """PRD can be rejected from review."""
        prd = self.Prd.create({"name": "Test PRD"})
        prd.action_submit_review()
        prd.action_reject()
        self.assertEqual(prd.state, "rejected")

    def test_version_increment(self):
        """Version bump should increment correctly."""
        prd = self.Prd.create({"name": "Test PRD"})
        prd.button_minor_version()
        self.assertEqual(prd.version, "1.1")
        prd.button_major_version()
        self.assertEqual(prd.version, "2.0")

    def test_compute_counts_empty(self):
        """Empty PRD should have zero counts."""
        prd = self.Prd.create({"name": "Test PRD"})
        self.assertEqual(prd.requirements_count, 0)
        self.assertEqual(prd.functions_count, 0)
        self.assertEqual(prd.requirements_percentage, 0.0)
        self.assertEqual(prd.functions_percentage, 0.0)

    def test_compute_counts_with_data(self):
        """Counts should reflect requirements and functions."""
        prd = self.Prd.create({"name": "Test PRD"})
        req1 = self.Req.create({
            "prd_id": prd.id, "code": "1.0", "name": "Req 1", "state": "done"
        })
        req2 = self.Req.create({
            "prd_id": prd.id, "code": "2.0", "name": "Req 2", "state": "draft"
        })
        func1 = self.Func.create({
            "prd_id": prd.id, "name": "Func 1", "state": "done"
        })
        # Force recompute
        prd.invalidate_recordset()
        self.assertEqual(prd.requirements_count, 2)
        self.assertEqual(prd.closed_requirements_count, 1)
        self.assertEqual(prd.requirements_percentage, 0.5)
        self.assertEqual(prd.functions_count, 1)
        self.assertEqual(prd.closed_functions_count, 1)
        self.assertEqual(prd.functions_percentage, 1.0)

    def test_action_requirements(self):
        """action_requirements should return correct window action."""
        prd = self.Prd.create({"name": "Test PRD"})
        action = prd.action_requirements()
        self.assertEqual(action["res_model"], "prd.requirement")
        self.assertEqual(action["domain"], [("prd_id", "=", prd.id)])

    def test_action_functions(self):
        """action_functions should return correct window action."""
        prd = self.Prd.create({"name": "Test PRD"})
        action = prd.action_functions()
        self.assertEqual(action["res_model"], "prd.function")
        self.assertEqual(action["domain"], [("prd_id", "=", prd.id)])


@tagged("post_install", "-at_install", "prd")
class TestPrdRequirement(TransactionCase):
    """Test requirement creation, parent hierarchy, and state transitions."""

    def setUp(self):
        super().setUp()
        self.Prd = self.env["prd.document"]
        self.Req = self.env["prd.requirement"]
        self.prd = self.Prd.create({"name": "Test PRD"})

    def test_create_requirement(self):
        """Requirement should be created with correct defaults."""
        req = self.Req.create({
            "prd_id": self.prd.id, "code": "1.0", "name": "Test Requirement"
        })
        self.assertEqual(req.state, "draft")
        self.assertEqual(req.priority, "must")
        self.assertEqual(req.prd_id, self.prd)

    def test_parent_hierarchy(self):
        """Parent requirement should be computed from code."""
        parent = self.Req.create({
            "prd_id": self.prd.id, "code": "1.0", "name": "Parent Req"
        })
        child = self.Req.create({
            "prd_id": self.prd.id, "code": "1.0.1", "name": "Child Req"
        })
        self.assertEqual(child.parent_id, parent)

    def test_no_parent_for_root(self):
        """Root-level requirement should have no parent."""
        req = self.Req.create({
            "prd_id": self.prd.id, "code": "1.0", "name": "Root Req"
        })
        self.assertFalse(req.parent_id)

    def test_state_transitions(self):
        """Requirement should support all 8 states."""
        req = self.Req.create({
            "prd_id": self.prd.id, "code": "1.0", "name": "Test"
        })
        valid_states = ["draft", "in_review", "approved", "ongoing",
                        "implemented", "verified", "done", "deferred"]
        for state in valid_states:
            req.state = state
            self.assertEqual(req.state, state)

    def test_priority_values(self):
        """Requirement should accept valid priorities."""
        for priority in ["must", "should", "could"]:
            req = self.Req.create({
                "prd_id": self.prd.id, "code": f"1.{priority}",
                "name": priority, "priority": priority,
            })
            self.assertEqual(req.priority, priority)

    def test_requirement_function_link(self):
        """Requirement should link to functions via prd.requirement.function."""
        func = self.env["prd.function"].create({
            "prd_id": self.prd.id, "name": "Test Function",
        })
        req = self.Req.create({
            "prd_id": self.prd.id, "code": "1.0", "name": "Test Req",
        })
        link = self.env["prd.requirement.function"].create({
            "prd_id": self.prd.id,
            "req_id": req.id,
            "func_id": func.id,
        })
        self.assertEqual(link.req_id, req)
        self.assertEqual(link.func_id, func)
        self.assertIn(func, req.function_ids.mapped("func_id"))


@tagged("post_install", "-at_install", "prd")
class TestPrdStakeholder(TransactionCase):
    """Test stakeholder creation, sign-off, and state tracking."""

    def setUp(self):
        super().setUp()
        self.Prd = self.env["prd.document"]
        self.Stakeholder = self.env["prd.stakeholder"]
        self.prd = self.Prd.create({"name": "Test PRD"})

    def test_create_stakeholder(self):
        """Stakeholder should be created with correct defaults."""
        sh = self.Stakeholder.create({
            "name": "Test Stakeholder",
            "prd_id": self.prd.id,
            "role": "approver",
        })
        self.assertEqual(sh.sign_off_state, "pending")
        self.assertEqual(sh.role, "approver")

    def test_approve_stakeholder(self):
        """Stakeholder should approve with timestamp."""
        sh = self.Stakeholder.create({
            "name": "Test Approver",
            "prd_id": self.prd.id,
            "role": "approver",
        })
        sh.action_approve()
        self.assertEqual(sh.sign_off_state, "approved")
        self.assertTrue(sh.sign_off_date)

    def test_reject_stakeholder(self):
        """Stakeholder should reject with timestamp."""
        sh = self.Stakeholder.create({
            "name": "Test Rejector",
            "prd_id": self.prd.id,
            "role": "reviewer",
        })
        sh.action_reject()
        self.assertEqual(sh.sign_off_state, "rejected")
        self.assertTrue(sh.sign_off_date)

    def test_stakeholder_counts(self):
        """PRD should compute stakeholder counts correctly."""
        self.Stakeholder.create({
            "name": "Approver 1", "prd_id": self.prd.id,
            "role": "approver", "sign_off_state": "approved",
        })
        self.Stakeholder.create({
            "name": "Approver 2", "prd_id": self.prd.id,
            "role": "approver", "sign_off_state": "pending",
        })
        self.Stakeholder.create({
            "name": "Reviewer 1", "prd_id": self.prd.id,
            "role": "reviewer",
        })
        self.prd.invalidate_recordset()
        self.assertEqual(self.prd.stakeholders_total_count, 3)
        self.assertEqual(self.prd.stakeholders_approved_count, 1)

    def test_roles(self):
        """All stakeholder roles should be valid."""
        for role in ["reviewer", "approver", "consulted", "informed", "responsible"]:
            sh = self.Stakeholder.create({
                "name": f"Role {role}",
                "prd_id": self.prd.id,
                "role": role,
            })
            self.assertEqual(sh.role, role)


@tagged("post_install", "-at_install", "prd")
class TestPrdTemplate(TransactionCase):
    """Test PRD template creation and PRD generation."""

    def setUp(self):
        super().setUp()
        self.Prd = self.env["prd.document"]
        self.Template = self.env["prd.template"]

    def test_create_template(self):
        """Template should be created with required fields."""
        tmpl = self.Template.create({
            "name": "Module Template",
            "document_type": "module",
        })
        self.assertEqual(tmpl.document_type, "module")
        self.assertTrue(tmpl.active)

    def test_create_prd_from_template(self):
        """Should create a PRD and requirements from template defaults."""
        tmpl = self.Template.create({
            "name": "Test Template",
            "document_type": "module",
            "goals": "Build a great module.",
            "user_persona": "Developer",
            "default_requirements": "1.0|Core|Core requirement|must\n1.1|Sub|Sub requirement|should",
        })
        result = tmpl.create_prd_from_template()
        self.assertEqual(result["res_model"], "prd.document")
        prd = self.Prd.browse(result["res_id"])
        self.assertTrue(prd.exists())
        self.assertIn("Test Template", prd.name)
        self.assertEqual(prd.goals, "Build a great module.")
        reqs = self.env["prd.requirement"].search([("prd_id", "=", prd.id)])
        self.assertEqual(len(reqs), 2)
        codes = reqs.mapped("code")
        self.assertIn("1.0", codes)
        self.assertIn("1.1", codes)

    def test_create_prd_empty_template(self):
        """Template without requirements should still create PRD."""
        tmpl = self.Template.create({
            "name": "Empty Template",
            "document_type": "other",
        })
        result = tmpl.create_prd_from_template()
        prd = self.Prd.browse(result["res_id"])
        self.assertTrue(prd.exists())
        reqs = self.env["prd.requirement"].search([("prd_id", "=", prd.id)])
        self.assertEqual(len(reqs), 0)


@tagged("post_install", "-at_install", "prd")
class TestPrdTraceability(TransactionCase):
    """Test traceability matrix generation."""

    def setUp(self):
        super().setUp()
        self.Prd = self.env["prd.document"]
        self.Req = self.env["prd.requirement"]
        self.Func = self.env["prd.function"]
        self.Traceability = self.env["prd.traceability"]
        self.prd = self.Prd.create({"name": "Test PRD"})

    def test_generate_traceability(self):
        """_generate_traceability_data should create matrix rows."""
        req = self.Req.create({
            "prd_id": self.prd.id, "code": "1.0", "name": "Test Req",
        })
        func = self.Func.create({
            "prd_id": self.prd.id, "name": "Test Func",
        })
        self.env["prd.requirement.function"].create({
            "prd_id": self.prd.id,
            "req_id": req.id,
            "func_id": func.id,
        })
        self.prd._generate_traceability_data()
        rows = self.Traceability.search([("prd_id", "=", self.prd.id)])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows.requirement_id, req)
        self.assertEqual(rows.function_id, func)
        self.assertEqual(rows.coverage_status, "partial")

    def test_traceability_unlinked_requirement(self):
        """Unlinked requirement should show as no coverage."""
        req = self.Req.create({
            "prd_id": self.prd.id, "code": "2.0", "name": "Orphan Req",
        })
        self.prd._generate_traceability_data()
        rows = self.Traceability.search([("prd_id", "=", self.prd.id)])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows.coverage_status, "none")
        self.assertFalse(rows.function_id)

    def test_traceability_full_coverage(self):
        """Requirement→Function→Task should be full coverage."""
        req = self.Req.create({
            "prd_id": self.prd.id, "code": "1.0", "name": "Full Req",
        })
        func = self.Func.create({
            "prd_id": self.prd.id, "name": "Full Func",
        })
        self.env["prd.requirement.function"].create({
            "prd_id": self.prd.id,
            "req_id": req.id,
            "func_id": func.id,
        })
        task = self.env["project.task"].create({
            "name": "Test Task",
        })
        func.task_id = task
        self.prd._generate_traceability_data()
        rows = self.Traceability.search([("prd_id", "=", self.prd.id)])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows.coverage_status, "full")
        self.assertEqual(rows.task_id, task)


@tagged("post_install", "-at_install", "prd")
class TestPrdFunction(TransactionCase):
    """Test function creation, state, and weight."""

    def setUp(self):
        super().setUp()
        self.Prd = self.env["prd.document"]
        self.Func = self.env["prd.function"]
        self.prd = self.Prd.create({"name": "Test PRD"})

    def test_create_function(self):
        """Function should be created with correct defaults."""
        func = self.Func.create({
            "prd_id": self.prd.id, "name": "Test Function",
        })
        self.assertEqual(func.state, "draft")
        self.assertEqual(func.weight, "1")

    def test_weight_values(self):
        """Function should accept all weight levels."""
        for weight in ["1", "2", "4", "8"]:
            func = self.Func.create({
                "prd_id": self.prd.id, "name": f"Func {weight}",
                "weight": weight,
            })
            self.assertEqual(func.weight, weight)

    def test_state_values(self):
        """Function should support all 8 states."""
        func = self.Func.create({
            "prd_id": self.prd.id, "name": "Test",
        })
        valid_states = ["draft", "in_review", "approved", "ongoing",
                        "implemented", "verified", "done", "deferred"]
        for state in valid_states:
            func.state = state
            self.assertEqual(func.state, state)
