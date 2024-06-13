# Python project Template

![python](https://img.shields.io/static/v1?label=Python&message=3.12&logo=Python&color=3776AB)
[![python-tests](https://github.com/HanaPoulpe/python-template/actions/workflows/run-python-tests.yml/badge.svg)](https://github.com/HanaPoulpe/hanaburtinnetcore/actions/workflows/run-python-tests.yml)
[![CodeQL](https://github.com/HanaPoulpe/python-template/actions/workflows/github-code-scanning/codeql/badge.svg)](https://github.com/HanaPoulpe/hanaburtinnetcore/actions/workflows/github-code-scanning/codeql)
[![codecov](https://codecov.io/github/{{reposirtory}}/graph/badge.svg?token={codecov-token})](https://codecov.io/github/HanaPoulpe/python-template)

# How to setup
## Install dependencies:

```shell
pip install -r requirements.txt
poetry install --with Dev
```

## Setup CI:

```shell
poetry run ci-python-tests create
poetry run ci-approval-bot create
```

## Setup pre-commit

```shell
pre-commit install
cp .pre-commit-config.yaml.example .pre-commit-config.yaml
```

Select your precommit hooks.

## Setup commit-linter

```shell
pre-commit install --hook-type commit-msg
```

Then enable the `Commit lint` section from your `.pre-commit-config.yaml`.

## Files cleanup

- [ ] Replace mentions of `python-template`, `python_template` by your project's name.
- [ ] Replace `HanaPoulpe/python-template` with your project repository name (`user/repositoru`).
- [ ] Replace `{codecov-token}` with your code-code token
