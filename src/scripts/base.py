import abc
import argparse
import contextlib
import os
import pathlib
import subprocess
import sys
from collections.abc import Callable, Generator
from typing import Any, ClassVar, Self, TextIO, cast

PROJECT_ROOT: pathlib.Path = pathlib.Path(__file__).parent.parent


class CommandError(Exception):
    pass


_COMMAND_REGISTER: dict[str, Callable[[], None]] = {}


class _BaseCommand(abc.ABC):
    name: ClassVar[str] = ""
    description: ClassVar[str] = ""

    cwd: ClassVar[str | pathlib.Path | None] = None

    @contextlib.contextmanager
    def set_cwd(self) -> Generator[None, None, None]:
        _cwd = pathlib.Path.cwd()
        if self.cwd is not None:
            os.chdir(self.cwd)

        yield
        os.chdir(_cwd)

    @abc.abstractmethod
    def handle(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError()

    def __call__(self) -> None:
        with self.set_cwd():
            self.handle()

    @classmethod
    def as_command(cls) -> Self:
        return cls()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not (name := cast(str, cls.name)):
            return

        _COMMAND_REGISTER[name] = cls.as_command()


class Command(_BaseCommand, abc.ABC):
    """
    Base class for commands with specific parser (mostly likely any new commands)
    """
    def get_parser(self) -> argparse.ArgumentParser:
        return argparse.ArgumentParser(prog=self.name, description=self.description)

    def add_arguments(self, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        return parser

    def __call__(self, args: list[str] | None = None) -> None:
        # Manage arguments
        args = args or sys.argv[1:]
        parser = self.get_parser()
        self.add_arguments(parser)
        arguments = parser.parse_args(args)

        # Handle command
        try:
            with self.set_cwd():
                self.handle(**vars(arguments))
        except CommandError as err:
            print(err, file=sys.stderr)
            exit(1)


class CommandWithParser(_BaseCommand, abc.ABC):
    """
    Base class for commands with existing commandline parser (like isort, etc...)
    """
    def __call__(self, args: list[str] | None = None) -> None:
        args = args or sys.argv[1:]

        try:
            with self.set_cwd():
                self.handle(*args)
        except CommandError as err:
            print(err, file=sys.stderr)
            exit(1)


class ExecCommand(Command):
    """
    Executes `command_name` with arguments provided by `get_args` method.

    - cwd - overwrites current working directory if existing
    """
    command_name: ClassVar[str] = ""

    cwd: ClassVar[str | pathlib.Path | None] = None

    def get_args(self, *args: Any, **kwargs) -> list[str]:
        return []

    def get_stdout(self, *args: Any, **kwargs) -> TextIO | None:
        return sys.stdout

    def get_stderr(self, *args: Any, **kwargs) -> TextIO | None:
        return sys.stderr

    def get_env(self, *args: Any, **kwargs) -> dict[str, str]:
        return {}

    def handle(self, *args: Any, **kwargs: Any) -> None:
        command_args = self.get_args(*args, **kwargs)

        process = subprocess.Popen(
            [self.command_name, *command_args],
            cwd=self.cwd,
            env=self.get_env(*args, **kwargs),
            stdout=self.get_stdout(*args, **kwargs),
            stderr=self.get_stderr(*args, **kwargs),
        )

        result = process.wait()

        if result != 0:
            raise CommandError()
