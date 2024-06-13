import argparse
import pathlib
from typing import ClassVar

from ruff import __main__ as ruff  # type: ignore

from scripts import base


class Ruff(base.ExecCommand):
    name = "ruff"
    command_name: ClassVar[str] = ruff.find_ruff_bin()
    description: ClassVar[str] = "Runs ruff linter of given files."

    def add_arguments(self, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        parser.add_argument("files", nargs="*", type=pathlib.Path)
        parser.add_argument("--fix", action="store_true")

        return parser

    def get_args(self, files: list[pathlib.Path], fix: bool) -> list[str]:
        args = ["check"]
        if fix:
            args.append("--fix")
        for file in files:
            args.append(str(file))

        return args
