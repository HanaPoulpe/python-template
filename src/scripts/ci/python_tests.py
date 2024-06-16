import argparse
import collections
from typing import Any, ClassVar

import termcolor

from scripts.python import tests as python_tests

from . import _base as base


class PythonBuildAction(base.Action):
    name: ClassVar[str] = "github_python_build"
    action_id: ClassVar[str] = "build"
    action_name: ClassVar[str] = "Build python application."

    def get_steps(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return [
            {
                "name": "Install git",
                "shell": "bash",
                "run": "apt update && apt install git -y",
            },
            {
                "name": "Checkout",
                "uses": "actions/checkout@v4",
            },
            {
                "name": "Install dependencies",
                "shell": "bash",
                "run": "\n".join([
                    "pip install -r requirements.txt",
                    "poetry install --with=dev",
                ]),
            },
        ]


class GitHubPythonTest(base.Workflow):
    name = "github_python_test"
    workflow_name: ClassVar[str] = "Python Tests"
    workflow_id: ClassVar[str] = "python-test"
    description: ClassVar[str] = "Creates python test workflow for github actions."

    def add_arguments(self, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        parser = super().add_arguments(parser)

        parser.add_argument(
            "tests",
            nargs="*",
            type=str,
            help="Tests to run",
        )
        parser.add_argument(
            "--required",
            type=str,
            nargs="*",
            help="Test required to pass the CI, values are ALL, NONE, or a list of tests",
        )
        parser.add_argument(
            "--coverage-fail-under",
            type=int,
            required=False,
            default=0,
            help="Fail if coverage is below <value> percent",
        )
        parser.add_argument(
            "--coverage-fail-regressed",
            type=bool,
            required=False,
            default=False,
            help="Fail if coverage has regressed",
        )

        return parser

    def get_jobs(
            self,
            *args: Any,
            **kwargs: Any,
    ) -> collections.OrderedDict[str, Any]:
        jobs: collections.OrderedDict[str, Any] = collections.OrderedDict()
        jobs = self.get_linters(jobs, *args, **kwargs)
        jobs = self.get_static_tests(jobs, *args, **kwargs)
        jobs = self.get_tests(jobs, *args, **kwargs)
        jobs = self.get_coverage(jobs, *args, **kwargs)
        jobs = self.get_tests_passed(jobs, *args, **kwargs)

        return jobs

    def get_linters(
            self,
            jobs: collections.OrderedDict[str, Any],
            tests: list[str] | None = None,
            *args: Any,
            **kwargs: Any,
    ) -> collections.OrderedDict[str, Any]:

        if not tests:
            ruff = self.prompt_bool("Do you want to run ruff?", default=True)
        else:
            ruff = "ruff" in tests or "ALL" in tests
        if ruff:
            jobs["ruff"] = {
                "name": "Python linter: ruff",
                "runs-on": "ubuntu-latest",
                "container": "python:3.12-slim-bookworm",
                "if": "${{ github.event_name == 'pull_request' }}",
                "steps": [
                    self.get_checkout(),
                    self.get_build(),
                    self.get_file_changed(),
                    {
                        "name": "Run ruff",
                        "id": "run-ruff",
                        "if": "${{ steps.file-changed.outputs.any_changed == 'true' }}",
                        "run": (
                            "poetry run python-ruff "
                            "${{ steps.file-changed.outputs.all_changed_files }}"
                        ),
                    },
                ],
            }

        if not tests:
            lock = self.prompt_bool("Do you want to run poetry lock check?", default=True)
        else:
            lock = "lock" in tests or "ALL" in tests
        if lock:
            jobs["lock"] = {
                "name": "Python linter: poetry lock check",
                "runs-on": "ubuntu-latest",
                "container": "python:3.12-slim-bookworm",
                "if": "${{ github.event_name == 'pull_request' }}",
                "steps": [
                    self.get_checkout(),
                    self.get_build(),
                    {
                        "name": "Run poetry lock check",
                        "id": "run-lock",
                        "run": "poetry lock --check",
                    },
                ],
            }

        return jobs

    def get_static_tests(
            self,
            jobs: collections.OrderedDict[str, Any],
            tests: list[str] | None = None,
            *args: Any,
            **kwargs: Any,
    ) -> collections.OrderedDict[str, Any]:
        if not tests:
            mypy = self.prompt_bool("Do you want to run mypy?", default=True)
        else:
            mypy = "mypy" in tests or "ALL" in tests
        if mypy:
            jobs["mypy"] = {
                "name": "Python linter: mypy",
                "runs-on": "ubuntu-latest",
                "container": "python:3.12-slim-bookworm",
                "if": "${{ github.event_name == 'pull_request' }}",
                "steps": [
                    self.get_checkout(),
                    self.get_build(),
                    self.get_file_changed(),
                    {
                        "name": "Run mypy",
                        "id": "run-mypy",
                        "run": (
                            "poetry run python-type-check "
                            "${{ steps.file-changed.outputs.all_changed_files }}"
                        ),
                    },
                ],
            }

        if not tests:
            importlinter = self.prompt_bool(
                "Do you want to run import linter?",
                default=True,
            )
        else:
            importlinter = "importlinter" in tests or "ALL" in tests
        if importlinter:
            jobs["importlinter"] = {
                "name": "Python linter: import linter",
                "runs-on": "ubuntu-latest",
                "container": "python:3.12-slim-bookworm",
                "if": "${{ github.event_name == 'pull_request' }}",
                "steps": [
                    self.get_checkout(),
                    self.get_build(),
                    self.get_file_changed(),
                    {
                        "name": "Run import linter",
                        "id": "run-importlinter",
                        "run": "poetry run python-check-imports",
                    },
                ],
            }

        return jobs

    def get_tests(
            self,
            jobs: collections.OrderedDict[str, Any],
            tests: list[str] | None = None,
            *args: Any,
            **kwargs: Any,
    ) -> collections.OrderedDict[str, Any]:
        all_tests = python_tests.get_all_tests()

        if not all_tests:
            if not tests:
                test_run = self.prompt_bool("Do you want to run pytest?", default=True)
            else:
                test_run = "pytest" in tests or "ALL" in tests
            jobs["pytest"] = {
                "name": "Python test",
                "runs-on": "ubuntu-latest",
                "container": "python:3.12-slim-bookworm",
                "steps": [
                    self.get_checkout(),
                    self.get_build(),
                    {
                        "name": "Run pytest",
                        "id": "run-pytest",
                        "run": "poetry run python-tests",
                    },
                ],
            }
            return jobs

        for test in all_tests:
            if not tests:
                test_run = self.prompt_bool(
                    f"Do you want to run {test.name}?",
                    default=True,
                )
            else:
                test_run = test.name in tests or "ALL" in tests
            if not test_run:
                continue

            jobs[test.name] = {
                "name": f"Python test: {test.name}",
                "runs-on": "ubuntu-latest",
                "container": "python:3.12-slim-bookworm",
                "steps": [
                    self.get_checkout(),
                    self.get_build(),
                    {
                        "name": f"Run {test.name}",
                        "id": f"run-{test.name.replace("_", "-")}",
                        "run": f"poetry run python-test-suite {test.name}",
                    },
                ],
            }

        return jobs

    def get_coverage(
        self,
        jobs: collections.OrderedDict[str, Any],
        tests: list[str] | None = None,
        coverage_fail_under: int | None = None,
        coverage_fail_regressed: bool | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> collections.OrderedDict[str, Any]:
        if not tests:
            coverage = self.prompt_bool("Do you want to run coverage?", default=True)
        else:
            coverage = "coverage" in tests or "ALL" in tests
        if coverage:
            fail_under_param = ""
            if coverage_fail_regressed:
                raise NotImplementedError()
            elif coverage_fail_under:
                fail_under_param = f"--fail-under={coverage_fail_under}"

            jobs["coverage"] = {
                "name": "Python test: coverage",
                "runs-on": "ubuntu-latest",
                "container": "python:3.12-slim-bookworm",
                "steps": [
                    self.get_checkout(),
                    self.get_build(),
                    {
                        "name": "Run coverage",
                        "id": "run-coverage",
                        "run": f"poetry run python-coverage {fail_under_param}",
                    },
                    {
                        "name": "Upload coverage",
                        "id": "upload-coverage",
                        "uses": "codecov/codecov-action@v4",
                        "with": {
                            "files": "coverage/report.xml",
                            "fail_ci_if_error": "true",
                            "verbose": "true",
                        },
                    },
                ],
            }

        return jobs

    def get_tests_passed(
        self,
        jobs: collections.OrderedDict[str, Any],
        required: list[str] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> collections.OrderedDict[str, Any]:
        all_required: list[str] = []

        for name in jobs:
            if required is None:
                test_required = self.prompt_bool(
                    f"Is {name} required for the CI?",
                    default=True,
                )
            else:
                test_required = name in required or "ALL" in required

            if test_required:
                all_required.append(name)

        if not all_required:
            return jobs

        jobs["python-tests-passed"] = {
            "name": "Python test: OK",
            "runs-on": "ubuntu-latest",
            "container": "python:3.12-slim-bookworm",
            "if": "${{ always() }}",
            "needs": all_required,
            "env": {
                "RESULTS": "\n".join([
                    f"${{{{ needs.{need}.result =='success' }}}}"
                    for need in all_required
                ]),
            },
            "steps": [{
                "id": "test-results",
                "name": "Test results",
                "run": "\n".join([
                    "echo ${{ RESULTS }}",
                    "for r in $RESULTS",
                    "do",
                    '    if [ $r = "success" ] || [ $r = "skipped" ];',
                    "    then",
                    "        true",
                    "    else",
                    '        echo "Some tests failed"',
                    "        exit 1",
                    "    fi",
                    "done",
                    'echo "All tests passed"',
                ]),
            }],
        }

        return jobs

    def create(self, *args: Any, **kwargs: Any) -> None:
        super().create(*args, **kwargs)

        build_action = PythonBuildAction.as_command()
        build_action(["create"])

    @staticmethod
    def get_checkout() -> dict[str, Any]:
        return {
            "name": "Checkout",
            "uses": "actions/checkout@v4",
        }

    @staticmethod
    def get_build() -> dict[str, Any]:
        return {
            "name": "Build",
            "uses": "./.github/actions/build",
        }

    @staticmethod
    def get_file_changed() -> dict[str, Any]:
        return {
            "name": "File changed",
            "id": "file-changed",
            "uses": "tj-actions/changed-files@v44",
            "with": {
                "files": "**/*.py",
            },
        }

    @staticmethod
    def prompt_bool(message: str, default: bool = True) -> bool:
        y = termcolor.colored("Y", "green", attrs=["bold"] if default else None)
        n = termcolor.colored("N", "red", attrs=["bold"] if not default else None)

        print(f"{message} [{y}/{n}]: ", end="")

        while (choice := input().lower()) not in ["y", "yes", "n", "no", ""]:
            print(f"{message} [{y}/{n}]: ", end="")

        return default if choice == "" else choice in ["y", "yes"]
