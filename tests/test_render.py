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


class TestCrossRepositoryIssueLink(unittest.TestCase):
    def test_issue_defaults_to_the_pull_request_repository(self):
        from mergeledger.render import evidence_links

        item = {
            "owner": "acme",
            "repo": "tool",
            "number": 7,
            "issue_number": 3,
            "verification": "tests",
        }
        self.assertIn("https://github.com/acme/tool/issues/3", evidence_links(item))

    def test_issue_can_live_in_another_repository(self):
        """Code and issues are often split across repositories. Falling back to
        the pull request's repository does not 404 -- GitHub redirects
        /issues/N to /pull/N -- so the link would quietly point at an unrelated
        pull request, which is worse than a dead link on an evidence card."""
        from mergeledger.render import evidence_links

        item = {
            "owner": "acme",
            "repo": "tool-cli",
            "number": 7,
            "issue_number": 3,
            "issue_repo": "tool",
            "verification": "tests",
        }
        links = evidence_links(item)
        self.assertIn("https://github.com/acme/tool/issues/3", links)
        self.assertNotIn("tool-cli/issues/3", links)

    def test_issue_owner_can_also_differ(self):
        from mergeledger.render import evidence_links

        item = {
            "owner": "fork-owner",
            "repo": "tool",
            "number": 7,
            "issue_number": 3,
            "issue_owner": "upstream-owner",
            "verification": "tests",
        }
        self.assertIn("https://github.com/upstream-owner/tool/issues/3", evidence_links(item))
