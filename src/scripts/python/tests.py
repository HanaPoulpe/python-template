import argparse
import contextlib
import pathlib
import sys
from typing import Any, ClassVar

import pytest
import termcolor
from importlinter import cli as importlinter
from mypy import main as mypy

import coverage
from scripts import base

_TEST_REGISTRY: list["Pytest"] = []


def _shell_path_to_file_names(path: str) -> list[pathlib.Path]:
    return list(base.PROJECT_ROOT.glob(path))


def get_all_tests() -> list["Pytest"]:
    return _TEST_REGISTRY


class Pytest(base.CommandWithParser, base.Command):
    """
    Base command for running pytest
    """
    name: ClassVar[str] = "pytest"
    description: ClassVar[str] = "Runs pytest"

    def handle(self, *args: Any, added_options: list[str] | None = None, **kwargs: Any):
        arguments = list(args) or [
            *(added_options or []),
            *self.get_default_options(),
                *self.get_default_files(),
            ]

        if pytest.cmdline.main(arguments):
            raise base.CommandError()

    def get_default_files(self) -> list[pathlib.Path | str]:
        return []

    def get_env(self, *args: Any, **kwargs: Any) -> dict[str, str]:
        """
        This brings the support of setting environment variables.
        Pytest supports local `pytest.ini` files that can be used
        to set environment variables.
        It would be a preferred way to set environment variables
        if the tests are in the same directory.
        """
        return {}

    def get_default_options(self, *args: Any, **kwargs: Any) -> list[str]:
        """
        Pytest supports local `pytest.ini` files that can be used to set flags.
        It would be a preferred way to set flags if the tests are in the same directory.
        """
        return []

    def __init__(self) -> None:
        super().__init__()

        if not getattr(self, "bypass", False):
            _TEST_REGISTRY.append(self)


class NamedPytest(base.Command):
    bypass: ClassVar[bool] = True
    name: ClassVar[str] = "test_suite"
    description: ClassVar[str] = "Runs a specific test suite"

    def add_arguments(self, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        parser.add_argument("names", nargs="*", type=str)

        return parser

    def handle(self, names: list[str] | None = None, *args: Any, **kwargs: Any) -> None:
        names = names or []

        has_failed = False
        summary: list[str] = []

        for test in get_all_tests():
            if test.name in names:
                try:
                    test.handle(*args, **kwargs)
                except base.CommandError:
                    summary.append(
                        f"{termcolor.colored("❌", "red")} {test.name:.<80}"
                        f"[{termcolor.colored("failed", "red")}].",
                    )
                    has_failed = True
                else:
                    summary.append(
                        f"{termcolor.colored("✅", "green")} {test.name:.<80}"
                        f"[{termcolor.colored("passed", "green")}].",
                    )

        if not summary:
            raise base.CommandError("No tests found.")

        for line in summary:
            print(line)

        if has_failed:
            raise base.CommandError("One or more tests failed.")


class AllPythonTests(Pytest):
    bypass: ClassVar[bool] = True
    name: ClassVar[str] = "all_tests"
    description: ClassVar[str] = "Runs all tests"

    def handle(
            self,
            *args: Any,
            added_options: list[str] | None = None,
            **kwargs: Any,
    ) -> None:
        self.get_parser().parse_args(args or sys.argv[1:])
        has_failed = False
        summary: list[str] = []

        for test in get_all_tests():
            try:
                test.handle(added_options=added_options)
            except base.CommandError:
                summary.append(
                    f"{termcolor.colored("❌", "red")} {test.name:.<80}"
                    f"[{termcolor.colored("failed", "red")}].",
                )
                has_failed = True
            else:
                summary.append(
                    f"{termcolor.colored("✅", "green")} {test.name:.<80}"
                    f"[{termcolor.colored("passed", "green")}].",
                )

        for line in summary:
            print(line)

        if has_failed:
            raise base.CommandError("One or more tests failed.")


class Coverage(base.Command):
    name: ClassVar[str] = "coverage"
    description: ClassVar[str] = """
    Runs coverage for all tests and create reports in `/coverage`.
    """
    bypass: ClassVar[bool] = True

    cwd: ClassVar[pathlib.Path] = base.PROJECT_ROOT

    def add_arguments(self, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        parser.add_argument(
            "--fail-under",
            type=int,
            required=False,
            default=0,
            help="Fail if coverage is below <value> percent",
        )
        parser.add_argument(
            "--no-report",
            required=False,
            default=False,
            help="Don't create report",
            action="store_true",
        )

        return parser

    def handle(self, fail_under: int, no_report: bool, *args: Any, **kwargs: Any) -> None:
        cov = coverage.Coverage()

        cov.start()
        for test in get_all_tests():
            with contextlib.suppress(base.CommandError):
                test.handle()
        cov.stop()

        if not no_report:
            cov.html_report()
            cov.xml_report()

        cov_rate = cov.report()

        if cov_rate < fail_under:
            raise base.CommandError(
                f"Coverage is below {fail_under}%. Current coverage is {cov_rate:.0f}%",
            )


class MyPy(base.CommandWithParser):
    name: ClassVar[str] = "mypy"
    description: ClassVar[str] = "Runs mypy type checker"

    cwd = base.PROJECT_ROOT
    default_files: ClassVar[list[str | pathlib.Path]] = [base.PROJECT_ROOT]

    def get_default_files(self) -> list[str]:
        return [str(f) for f in self.default_files]

    def handle(self, *args: Any, **kwargs: Any) -> None:
        try:
            mypy.main(args=list(args) or self.get_default_files(), clean_exit=True)
        except SystemExit as err:
            raise base.CommandError() from err


class ImportLinter(base.Command):
    name: ClassVar[str] = "import_linter"
    description: ClassVar[str] = "Checks for forbidden imports."
    cwd = base.PROJECT_ROOT.parent

    def handle(self, *args: Any, **kwargs: Any) -> None:
        if importlinter.lint_imports():
            raise base.CommandError()
