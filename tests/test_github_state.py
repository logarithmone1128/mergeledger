import unittest

from mergeledger.github import normalized_state


class TestNormalizedState(unittest.TestCase):
    def test_merged_wins(self):
        self.assertEqual(
            normalized_state({"state": "closed", "merged_at": "2026-08-01T00:00:00Z"}), "merged"
        )

    def test_closed_without_merge(self):
        self.assertEqual(normalized_state({"state": "closed", "merged_at": None}), "closed")

    def test_open_without_review_evidence_is_submitted(self):
        """The state this project exists to keep separate: an open pull request
        nobody has looked at is submitted, not under review."""
        pull_request = {
            "state": "open",
            "merged_at": None,
            "draft": False,
            "requested_reviewers": [],
            "requested_teams": [],
        }
        self.assertEqual(normalized_state(pull_request, reviews=[]), "submitted")

    def test_open_with_a_submitted_review(self):
        pull_request = {"state": "open", "merged_at": None, "draft": False}
        reviews = [{"state": "COMMENTED"}]
        self.assertEqual(normalized_state(pull_request, reviews), "under_review")

    def test_open_with_a_requested_reviewer(self):
        pull_request = {
            "state": "open",
            "merged_at": None,
            "draft": False,
            "requested_reviewers": [{"login": "maintainer"}],
        }
        self.assertEqual(normalized_state(pull_request, reviews=[]), "under_review")

    def test_open_with_a_requested_team(self):
        pull_request = {
            "state": "open",
            "merged_at": None,
            "draft": False,
            "requested_teams": [{"slug": "reviewers"}],
        }
        self.assertEqual(normalized_state(pull_request, reviews=[]), "under_review")

    def test_draft_is_never_under_review(self):
        pull_request = {
            "state": "open",
            "merged_at": None,
            "draft": True,
            "requested_reviewers": [{"login": "maintainer"}],
        }
        self.assertEqual(normalized_state(pull_request, reviews=[{"state": "COMMENTED"}]), "submitted")


if __name__ == "__main__":
    unittest.main()
