# Contributing Code

We'd love to accept your patches and contributions to this project. This page
contains a number of instructions and guidelines that you may want to follow
so your PR can get merged in a timely manner.

## Setup

While for using LibreLane, we recommend any of the installation methods, for
development we _really_ recommend
{doc}`docs/source/installation/nix_installation/index`. Nix allows you to demo
changes with LibreLane and/or tools quite easily.

This guide will assume you have LibreLane installed via Nix.

When developing LibreLane, you want to run `nix develop .#dev`. This will allow
you to run YOUR current edits to LibreLane using `python3 -m librelane <args>`,
except it will not attempt to build LibreLane itself as part of the Nix
environment.

## Branching

For various reasons, it's recommended to call working branches, even in your
forks, something else other than `master`, `main`, or `dev` as these branch
names do have some special behavior associated with them.

```{note}
The `main` branch is the stable branch for LibreLane, i.e., this branch is
updated less frequently and only accepts bugfixes.

Feature contributions should be directed towards the `dev` branch.
```

## Testing

Before you submit your changes, it's prudent to perform some kind of smoke test.
`python3 -m librelane --smoke-test` tests a simple spm design to ensure nothing
has gone horribly wrong.

LibreLane also runs two sets of tests per PR, namely, a set of **design tests**
and a set of **unit tests**. Unit tests are further broken down into
**infrastructure tests** and **step implementation tests**.

You do not have to run the design tests yourself, but we do require you to run
the unit tests. To do so, in the `nix develop .#dev` environment, run:

```bash
git submodule update --init ./test/steps/all
# To run all tests:
pytest -n auto -m all
# To run just the infrastructure tests:
#   * We don't bother passing (-n auto) to this test because the time taken to
#     allocate workers exceeds the time taken to run the tests.
pytest
# To run just step implementation tests:
pytest -n auto -m step_impl_test
```

### Dealing with failures

Infrastructure unit tests must be fixed. Collaborate with maintainers if you're
not sure why something is failing.

Step implementations unit tests, as you may have surmised, are not stored in
this repo (to save on clone times), and are stored in a submodule. This
complicates pull requests, as you have to open two pull requests across two
repos.

If the issue is simple (an error code needs to be updated or similar), you may
elect to exclude the test from running by adding it to `test/steps/xfails`.

The same goes for design tests: if the failure is simple enough to fix, you may
simply comment out the relevant design in `.github/test_sets/test_sets.yml`.

## Language Standards

### Python

Python code should be written for Python 3.10+, and be **typed**. i.e., we
require explicit type annotations for all major API functions.

You will need to ensure that your Python code passes linting with our three
chosen tools (and one optional tool):

```{list-table}
:header-rows: 1
:widths: 10 10 15 75

* - Tool
  - Kind
  - Command
  - Description
* - [black](https://github.com/psf/black)
  - [Formatter](https://en.wikipedia.org/wiki/Prettyprint#Programming_code_formatting)
  - `black .`
  - Ensures indentation and whitespace follow a strict standard without having you lift a finger.
* - [flake8](https://github.com/pycqa/flake8)
  - [Linter](https://en.wikipedia.org/wiki/Lint_(software)>)
  - `flake8 .`
  - Finds a number of common programming pitfalls.
* - [mypy](https://github.com/python/mypy)
  - [Type-Checker](https://en.wikipedia.org/wiki/Type_system#Type_checking)
  - `mypy .`
  - Ensures that you're using compatible types, i.e., you are not passing a `string` to a function that accepts an `int`, or passing `None` to a non-optional variable, and such.
* - [ruff](https://github.com/astral-sh/ruff) (optional)
  - [Linter](https://en.wikipedia.org/wiki/Lint_(software)>)
  - `ruff check .`
  - Our `pyproject.toml` uses ruff as a simple parsing checker, i.e., makes sure
    your code can still parse under Python 3.10 as it is entirely too easy to
    write code that by accident only works on later versions of Python. We
    presently do not use other features of ruff.
```

Do all arithmetic either in integers or using the Python
[`decimal`](https://docs.python.org/3.10/library/decimal.html) library. All
(numerous) existing uses of IEEE-754 are bugs we are interested in fixing.

### Tcl

Only use Tcl to interface with tools that only have a Tcl interface (or have an
immature Python interface)- i.e., Yosys, OpenROAD and Magic.

1TBS-indented, four spaces, `lower_snake_case` for local/global variables and
`UPPER_SNAKE_CASE` for environment variables. Unfortunately it is impossible to
add any other guidelines or standards to the Tcl code considering it is Tcl
code. Please exercise your best judgment.

#### Yosys, OpenROAD and Magic Scripts

There are some special guidelines for scripts in `scripts/yosys`,
`scripts/openroad`, and `scripts/magic`:

* The scripts for each tool are a self-contained ecosystem: do not `source`
  scripts from outside their directories.
  * You may duplicate functionality if you deem it necessary.
* Do not reference the following environment variables anywhere in order to
  avoid causing recursion when generating issue reproducibles:
  * $PWD
  * $RUN_DIR
  * $DESIGN_DIR

## Submissions

Make your changes and then submit them as a pull requests to the:

* `main` branch: For bugfixes.
* `dev` branch: For new features.

Consult [GitHub Help](https://help.github.com/articles/about-pull-requests/) for
more information on using pull requests.

You need to understand what code you are changing, what the change does, and
justify that change in the commit messages and PR.

All code contributions must follow the {doc}`/contributors/llm-policy`.

### The Approval Process

For a PR to be merged, there are two requirements:

* There are two automated checks, one for linting and the other for
  functionality. Both must pass.
* An LibreLane team member must inspect and approve the PR.

## Licensing and Copyright

Please note all code contributions must have the same license as LibreLane,
i.e., the Apache License, version 2.0. You, as the submitter of the patch, are
responsible for your patch, regardless of where that change came from; whether
you:

1. Wrote it yourself and are willing to release your changes under said license.
2. Acquired it from other libre software with compatible license terms (and of
   course the requisite copyright notices.)

For significant changes, please add your (or your employer's) name to the
Authors.md file at the root of the repository.
