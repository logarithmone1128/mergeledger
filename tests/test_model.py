import unittest

from mergeledger.model import audit_ledger


def valid_ledger():
    return {
        "schema_version": 1,
        "items": [
            {
                "owner": "example",
                "repo": "tool",
                "number": 7,
                "theme": "Reliability",
                "stack": "Python",
                "change": "Handled a bounded failure.",
                "verification": "focused tests",
                "state": "under_review",
                "merged_at": None,
            }
        ],
    }


class AuditTests(unittest.TestCase):
    def test_valid_ledger(self):
        self.assertEqual(audit_ledger(valid_ledger()), [])

    def test_merged_claim_requires_merged_at(self):
        ledger = valid_ledger()
        ledger["items"][0]["state"] = "merged"
        self.assertIn("merged claim requires", "\n".join(audit_ledger(ledger)))

    def test_private_identity_fields_are_rejected(self):
        ledger = valid_ledger()
        ledger["profile"] = {"company": "Private Employer"}
        self.assertIn("private identity field", "\n".join(audit_ledger(ledger)))

    def test_email_addresses_are_rejected_anywhere(self):
        ledger = valid_ledger()
        ledger["items"][0]["change"] = "Contact person@example.com for details."
        self.assertIn("email address detected", "\n".join(audit_ledger(ledger)))


if __name__ == "__main__":
    unittest.main()
