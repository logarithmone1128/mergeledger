<p align="center">
  <img src="./assets/mergeledger-signal.svg" alt="mergeledger evidence pipeline" width="100%" />
</p>

`mergeledger` turns open-source contribution evidence into a public Markdown
ledger without upgrading an open pull request into a merged claim.

It is built for contributors, job seekers, and portfolio maintainers who want
their public record to remain useful, current, and defensible.

## Why

GitHub profiles and resumes often collapse five different states into one word:
"contributed". A patch prepared locally, a submitted pull request, maintainer
review, and an accepted merge are not the same evidence.

`mergeledger` keeps those states explicit, and `mergeledger verify` checks each
one against GitHub so a claim cannot outrun its evidence:

```text
prepared → submitted → under_review → merged
                                  ↘ closed
```

## Install

```bash
git clone https://github.com/logarithmone1128/mergeledger.git
cd mergeledger
python3 -m pip install .
```

Python 3.9+ is supported. The runtime has no third-party dependencies.

## Use

Check structure and privacy boundaries, offline:

```bash
mergeledger audit examples/contributions.json
```

Check every claim against GitHub, and fail on any overstatement:

```bash
mergeledger verify contributions.json
```

`audit` is offline and deliberately limited: it checks that the ledger is
well-formed and free of private identity data. It cannot tell whether a claim is
true, because `merged_at` is written by the ledger's own author -- a `merged`
state with a hand-written timestamp passes `audit` and fails `verify`. Run
`verify` before publishing anything.

Refresh pull-request states from GitHub:

```bash
mergeledger refresh contributions.json
```

Render profile-ready Markdown cards:

```bash
mergeledger render contributions.json --output CONTRIBUTIONS.md
```

Set `GH_TOKEN` or `GITHUB_TOKEN` to increase GitHub API limits. The token is
read from the environment and is never written to the ledger.

## Claim gate

The audit fails when:

- an item claims `merged` without an authoritative `merged_at` timestamp;
- `merged_at` conflicts with the declared state;
- a required evidence field is absent;
- employer, company, school, education, location, legal name, phone, or email
  data appears in the public ledger.

The renderer keeps the current state and the supporting evidence visibly
separate. It does not generate vanity metrics, contribution-count claims, or
maintainer titles.

## Ledger format

```json
{
  "schema_version": 1,
  "items": [
    {
      "owner": "example-org",
      "repo": "agent-cli",
      "number": 42,
      "issue_number": 39,
      "theme": "Least privilege",
      "stack": "Go",
      "change": "Made an optional integration request only the permission it uses.",
      "verification": "focused tests, package tests, race suite",
      "state": "under_review",
      "merged_at": null
    }
  ]
}
```

## Development

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m mergeledger.cli audit examples/contributions.json
PYTHONPATH=src python3 -m mergeledger.cli render examples/contributions.json
```

## Roadmap

- README section replacement with stable markers
- JSON Schema publication
- release assets for `pipx` installation
- optional repository health and review-latency signals

## License

MIT
