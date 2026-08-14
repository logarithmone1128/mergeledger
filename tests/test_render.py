import unittest

from mergeledger.render import render_cards


class RenderTests(unittest.TestCase):
    def test_cards_keep_state_and_evidence_separate(self):
        rendered = render_cards(
            [
                {
                    "owner": "example",
                    "repo": "tool",
                    "number": 7,
                    "issue_number": 5,
                    "theme": "Reliability",
                    "stack": "Python",
                    "change": "Handled a bounded failure.",
                    "verification": "focused tests",
                    "state": "under_review",
                }
            ]
        )
        self.assertIn("**Reliability** · `Python` · **Under review**", rendered)
        self.assertIn("Evidence → [Issue #5]", rendered)
        self.assertNotIn("Merged", rendered)


if __name__ == "__main__":
    unittest.main()
