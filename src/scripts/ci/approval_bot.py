import argparse
import collections
from typing import Any, ClassVar

from . import _base as base


class ApprovalBot(base.Workflow):
    name: ClassVar[str] = "github_approval_bot"
    workflow_name: ClassVar[str] = "Approval Bot"
    workflow_id: ClassVar[str] = "approval-bot"
    description = "Automatically approve pull requests."

    def add_arguments(self, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        parser = super().add_arguments(parser)

        parser.add_argument(
            "--owner",
            "-o",
            action="store_true",
            help="Automatically approve pull requests from owner.",
        )
        parser.add_argument(
            "--dependabot",
            "-d",
            action="store_true",
            help="Automatically approve pull requests from dependabot.",
        )
        parser.add_argument(
            "--commit-linter",
            "-l",
            action="store_true",
            help="Run commit linter on the pull requests.",
        )
        parser.add_argument(
            "--clear-automerge",
            "-c",
            action="store_true",
            help=(
                "Clear automerge on the pull requests, "
                "--dependabot includes this option."
            ),
        )

        return parser

    def get_jobs(
            self,
            *args: Any,
            owner: bool = False,
            dependabot: bool = False,
            commit_linter: bool = False,
            clear_automerge: bool = False,
            **kwargs: Any,
    ) -> collections.OrderedDict[str, Any]:
        jobs: collections.OrderedDict[str, Any] = collections.OrderedDict()

        if clear_automerge or dependabot:
            jobs["clear-automerge"] = {
                "name": "Clear automerge",
                "runs-on": "ubuntu-latest",
                "steps": [{
                    "name": "Disable auto - merge",
                    "run": 'gh pr merge - -disable - auto - -merge "$PR_URL" || true',
                    "env": {
                        "PR_URL": "${{github.event.pull_request.html_url}}",
                        "GITHUB_TOKEN": "${{secrets.GITHUB_TOKEN}}",
                    },
                }],
            }

        if owner:
            jobs["auto-approve-owner"] = {
                "name": "Auto approve owner",
                "runs-on": "ubuntu-latest",
                "if": (
                    "${{github.event.pull_request.user.login == "
                    "github.repository_owner}}"
                ),
                "steps": [{
                    "name": "Auto approve owner",
                    "run": 'gh pr review "$PR_URL" --approve',
                    "env": {
                        "PR_URL": "${{github.event.pull_request.html_url}}",
                        "GITHUB_TOKEN": "${{secrets.GITHUB_TOKEN}}",
                    },
                }],
            }

        if dependabot:
            jobs["auto-approve-dependabot"] = {
                "name": "Auto approve dependabot",
                "runs-on": "ubuntu-latest",
                "needs": ["clear-automerge"],
                "if": "${{github.event.pull_request.user.login == 'dependabot[bot]'}}",
                "steps": [
                    {
                        "name": "Dependabot metadata",
                        "id": "dependabot-metadata",
                        "uses": "dependabot/fetch-metadata@v2.1.0",
                    },
                    {
                        "name": "Approve patch and minor updates",
                        "if": (
                            "${{steps.dependabot-metadata.outputs.update-type"
                            " == 'version-update:semver-patch' || "
                            "steps.dependabot-metadata.outputs.update-type "
                            "== 'version-update:semver-minor'}}"
                        ),
                        "run": (
                            'gh pr review "$PR_URL" --approve -b '
                            "\"I'm **approving** this pull request because "
                            '**it includes a patch or minor update**"'
                        ),
                        "env": {
                            "PR_URL": "${{github.event.pull_request.html_url}}",
                            "GITHUB_TOKEN": "${{secrets.GITHUB_TOKEN}}",
                        },
                    },
                    {
                        "name": "Approve major updates of development dependencies",
                        "if": (
                            "${{steps.dependabot-metadata.outputs.update-type "
                            "== 'version-update:semver-major' && "
                            "steps.dependabot-metadata.outputs.dependency-type"
                            " == 'direct:development'}}"
                        ),
                        "run": (
                            'gh pr review "$PR_URL" --approve -b '
                            "\"I'm **approving** this pull request because "
                            "**it includes a major update of a dependency "
                            'only used in development**"'
                        ),
                    },
                    {
                        "name": "Comment major updates of production dependencies",
                        "if": (
                            "${{steps.dependabot-metadata.outputs.update-type"
                            " == 'version-update:semver-major' "
                            "&& steps.dependabot-metadata.outputs."
                            "dependency-type == 'direct:production'}}"
                        ),
                        "run": "\n".join([
                            "gh pr comment $PR_URL --body "
                            "\"I'm **not approving** this PR because "
                            "**it includes a major update of a "
                            'dependency used in production**"',
                            "gh pr edit $PR_URL "
                            '--add-label "requires-manual-qa"',
                            "gh pr edit $PR_URL "
                            "--add-assignee ${{ github.repository_owner }}",
                        ]),
                        "env": {
                            "PR_URL": "${{github.event.pull_request.html_url}}",
                            "GITHUB_TOKEN": "${{secrets.GITHUB_TOKEN}}",
                        },
                    },
                    {
                        "name": "Enable auto merge",
                        "if": "${{ github.event.pull_request.assignees != null }}",
                        "run": 'gh pr merge --auto --merge "$PR_URL"',
                        "env": {
                            "PR_URL": "${{github.event.pull_request.html_url}}",
                            "GITHUB_TOKEN": "${{secrets.GITHUB_TOKEN}}",
                        },
                    },
                ],
            }

        if commit_linter:
            jobs["commit-linter"] = {
                "name": "Commit linter",
                "runs-on": "ubuntu-latest",
                "if": "${{ github.event.pull_request.user.login != 'dependabot[bot]' }}",
                "steps": [
                    {
                        "name": "Check commit messages",
                        "uses": "opensource-nepal/commitlint@v1",
                    },
                ],
            }

        return jobs

    def get_triggers(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {
            "pull_request": {
                "branches": ["main"],
            },
        }

    def get_permissions(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {
            "contents": "write",
            "pull-requests": "write",
        }
