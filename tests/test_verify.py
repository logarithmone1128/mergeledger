import unittest

from mergeledger.model import compare_claim, verify_ledger


def item(state, **kw):
    base = {"owner": "acme", "repo": "tool", "number": 7, "state": state}
    base.update(kw)
    return base


class TestCompareClaim(unittest.TestCase):
    def test_merged_claim_on_an_open_pull_request_is_caught(self):
        """The failure this project exists to prevent. Structural validation
        passes it, because merged_at is written by the ledger's own author."""
        findings = compare_claim(
            item("merged", merged_at="2026-08-20T00:00:00Z"), "under_review", None, 0
        )
        self.assertTrue(any("claims 'merged'" in f for f in findings))

    def test_matching_claim_is_clean(self):
        self.assertEqual(compare_claim(item("under_review"), "under_review", None, 0), [])

    def test_understated_claim_is_reported_as_drift(self):
        findings = compare_claim(item("submitted"), "under_review", None, 0)
        self.assertTrue(any("refresh the ledger" in f for f in findings))

    def test_merged_claim_on_a_closed_pull_request(self):
        findings = compare_claim(item("merged", merged_at="x"), "closed", None, 0)
        self.assertTrue(any("closed without merging" in f for f in findings))

    def test_live_claim_on_a_closed_pull_request(self):
        findings = compare_claim(item("under_review"), "closed", None, 0)
        self.assertTrue(any("is closed" in f for f in findings))

    def test_merged_at_must_match_upstream(self):
        findings = compare_claim(
            item("merged", merged_at="2026-01-01T00:00:00Z"),
            "merged",
            "2026-08-20T00:00:00Z",
            0,
        )
        self.assertTrue(any("does not match upstream" in f for f in findings))

    def test_genuine_merge_is_clean(self):
        findings = compare_claim(
            item("merged", merged_at="2026-08-20T00:00:00Z"),
            "merged",
            "2026-08-20T00:00:00Z",
            0,
        )
        self.assertEqual(findings, [])


class TestVerifyLedger(unittest.TestCase):
    def test_unreachable_item_becomes_a_finding_not_a_crash(self):
        def resolve(_):
            raise RuntimeError("404")

        findings = verify_ledger({"items": [item("submitted")]}, resolve)
        self.assertTrue(any("could not verify against upstream" in f for f in findings))

    def test_clean_ledger_produces_no_findings(self):
        findings = verify_ledger(
            {"items": [item("under_review")]}, lambda _: ("under_review", None)
        )
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
