import abc
import argparse
import collections
import os
import pathlib
from collections.abc import Callable
from typing import Any, ClassVar

import yaml

from scripts import base

BASE_WORKFLOW_DIR = base.PROJECT_ROOT.parent.joinpath(".github", "workflows")
BASE_ACTION_DIR = base.PROJECT_ROOT.parent.joinpath(".github", "actions")


yaml.add_representer(
    collections.OrderedDict,
    lambda self, data: self.represent_mapping(
        "tag:yaml.org,2002:map",
        data.items(),
    ),
)


def multiline_str_representer(dumper: yaml.Dumper, data: str) -> Any:
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.add_representer(str, multiline_str_representer)


class Workflow(base.Command, abc.ABC):
    workflow_name: ClassVar[str] = ""
    workflow_id: ClassVar[str] = ""
    description: ClassVar[str] = ""

    def get_workflow_definition(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        workflow: collections.OrderedDict[str, Any] = collections.OrderedDict()
        workflow["name"] = self.workflow_name
        workflow["run-name"] = self.workflow_id

        if permissions := self.get_permissions():
            workflow["permissions"] = permissions

        workflow["on"] = self.get_triggers(*args, **kwargs)
        workflow["jobs"] = self.get_jobs(*args, **kwargs)

        return workflow

    def get_jobs(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError()

    def get_triggers(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {
            "push": {
                "branches": ["main"],
            },
            "pull_request": {
                "branches": ["main"],
            },
        }

    def get_permissions(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {}

    def add_arguments(self, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        subparsers = parser.add_subparsers(
            help="Workflow commands",
        )
        delete = subparsers.add_parser("delete", help="Delete workflow")
        delete.set_defaults(func=self.delete)

        create = subparsers.add_parser("create", help="Create workflow")
        create.set_defaults(func=self.create)

        return create

    def handle(
            self,
            *args: Any,
            func: Callable[..., None] | None = None,
            **kwargs: Any,
    ) -> None:
        if not func:
            raise base.CommandError("No command provided. Use `add` or `delete` command.")

        func(*args, **kwargs)

    @property
    def workflow_path(self) -> pathlib.Path:
        return BASE_WORKFLOW_DIR.joinpath(f"{self.workflow_id}.yml")

    def create(self, *args: Any, **kwargs: Any) -> None:
        self.workflow_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.workflow_path, "w") as f:
            yaml.dump(
                self.get_workflow_definition(*args, **kwargs),
                f,
            )

    def delete(self) -> None:
        if self.workflow_path.exists():
            os.remove(self.workflow_path)


class Action(base.Command, abc.ABC):
    action_name: ClassVar[str] = ""
    action_id: ClassVar[str] = ""
    description: ClassVar[str] = ""

    using: ClassVar[str] = "composite"

    def get_steps(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return []

    def get_action_definition(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {
            "name": self.action_name,
            "description": self.description,
            "runs": {
                "using": self.using,
                "steps": self.get_steps(*args, **kwargs),
            },
        }

    def add_arguments(self, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        subparsers = parser.add_subparsers(
            help="Action commands",
        )
        delete = subparsers.add_parser("delete", help="Delete action")
        delete.set_defaults(func=self.delete)

        create = subparsers.add_parser("create", help="Create action")
        create.set_defaults(func=self.create)

        return create

    def handle(
            self,
            *args: Any,
            func: Callable[..., None] | None = None,
            **kwargs: Any,
    ) -> None:
        if not func:
            raise base.CommandError("No command provided. Use `add` or `delete` command.")

        func(*args, **kwargs)

    @property
    def action_path(self) -> pathlib.Path:
        return BASE_ACTION_DIR.joinpath(self.action_id)

    def create(self, *args: Any, **kwargs: Any) -> None:
        self.action_path.mkdir(parents=True, exist_ok=True)

        with open(self.action_path.joinpath("action.yml"), "w") as f:
            yaml.dump(
                self.get_action_definition(*args, **kwargs),
                f,
            )

    def delete(self) -> None:
        os.remove(self.action_path.joinpath("action.yml"))
