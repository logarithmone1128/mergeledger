import os
import unittest

from mergeledger.model import audit_privacy, load_private_terms


class TestFreeTextPrivacy(unittest.TestCase):
    """Structured keys are not where leaks happen. Nobody adds a field called
    "employer"; they mention it in a change description."""

    def test_declared_term_in_free_text_is_caught(self):
        ledger = {"items": [{"change": "Fixed while working at Initech on the payroll migration."}]}
        findings = audit_privacy(ledger, ["Initech"])
        self.assertTrue(any("private term 'Initech'" in f for f in findings))

    def test_matching_is_case_insensitive(self):
        ledger = {"items": [{"change": "reported by the INITECH team"}]}
        self.assertTrue(audit_privacy(ledger, ["Initech"]))

    def test_no_terms_declared_means_no_term_findings(self):
        ledger = {"items": [{"change": "Fixed while working at Initech."}]}
        self.assertEqual(audit_privacy(ledger, []), [])

    def test_phone_number_is_caught(self):
        ledger = {"items": [{"note": "call +1 415 555 0100"}]}
        findings = audit_privacy(ledger)
        self.assertTrue(any("phone number" in f for f in findings), findings)

    def test_issue_number_is_not_mistaken_for_a_phone_number(self):
        ledger = {"items": [{"number": 5146, "issue_number": 5057, "change": "PR #5146"}]}
        self.assertEqual([f for f in audit_privacy(ledger) if "phone" in f], [])

    def test_private_terms_inside_the_ledger_is_itself_a_finding(self):
        """The ledger gets published, so storing the terms in it would leak
        exactly what they are meant to protect."""
        ledger = {"private_terms": ["Initech"], "items": []}
        findings = audit_privacy(ledger, [])
        self.assertTrue(any("must not be stored in the ledger" in f for f in findings))


class TestLoadPrivateTerms(unittest.TestCase):
    def test_reads_from_environment_with_comments_and_blanks(self):
        os.environ["MERGELEDGER_PRIVATE_TERMS"] = "Initech\n# a comment\n\nSpringfield"
        try:
            self.assertEqual(load_private_terms(), ["Initech", "Springfield"])
        finally:
            del os.environ["MERGELEDGER_PRIVATE_TERMS"]

    def test_comma_separated_is_accepted(self):
        os.environ["MERGELEDGER_PRIVATE_TERMS"] = "Initech, Springfield"
        try:
            self.assertEqual(load_private_terms(), ["Initech", "Springfield"])
        finally:
            del os.environ["MERGELEDGER_PRIVATE_TERMS"]

    def test_absent_environment_yields_nothing(self):
        os.environ.pop("MERGELEDGER_PRIVATE_TERMS", None)
        self.assertEqual(load_private_terms(), [])


if __name__ == "__main__":
    unittest.main()


class TestPhoneFalsePositives(unittest.TestCase):
    """Caught by running the checker on a real ledger: a refreshed_at timestamp
    is digit-dense enough to look like a phone number."""

    def test_iso_timestamp_is_not_a_phone_number(self):
        from mergeledger.model import looks_like_phone

        self.assertFalse(looks_like_phone("2026-08-25T02:15:37.836797+00:00"))

    def test_plain_date_is_not_a_phone_number(self):
        from mergeledger.model import looks_like_phone

        self.assertFalse(looks_like_phone("merged on 2026-08-20"))

    def test_version_string_is_not_a_phone_number(self):
        from mergeledger.model import looks_like_phone

        self.assertFalse(looks_like_phone("erpnext v15.115.0 and frappe 16.31.0"))

    def test_a_real_phone_number_still_is(self):
        from mergeledger.model import looks_like_phone

        self.assertTrue(looks_like_phone("call +1 415 555 0100"))

    def test_a_phone_number_next_to_a_timestamp_still_is(self):
        from mergeledger.model import looks_like_phone

        self.assertTrue(looks_like_phone("2026-08-25T02:15:37Z, call +1 415 555 0100"))
