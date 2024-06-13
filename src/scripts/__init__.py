import importlib
import pathlib
from collections.abc import Callable, Generator

from . import base


def _walk_files(
        path: pathlib.Path, exclude_current: bool,
) -> Generator[pathlib.Path, None, None]:
    for entry in path.iterdir():
        if entry.is_dir():
            yield from _walk_files(entry, False)
        elif (
                not exclude_current
                and entry.is_file()
                and not entry.name.startswith("_")
                and entry.suffix == ".py"
        ):
            yield entry


def _import_all_modules() -> None:
    for file in _walk_files(pathlib.Path(__file__).parent, True):
        import_name = str(
            file.relative_to(pathlib.Path(__file__).parent),
        ).replace("/", ".")[:-3]
        importlib.import_module(f".{import_name}", __package__)


_import_all_modules()


def __getattr__(name: str) -> Callable[[], None]:
    return base._COMMAND_REGISTER[name]


def __dir__() -> list[str]:
    return list(base._COMMAND_REGISTER.keys())


__all__ = __dir__()
