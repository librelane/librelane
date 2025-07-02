# Contributing Code

We'd love to accept your patches and contributions to this project. There are
just a few small guidelines you need to follow.

## Branching

For various reasons, it's recommended to call working branches, even in your
forks, something else other than `master` or `main`, as those two branch names
do have some special behavior associated with them.

## Testing

Before you submit your changes, it's prudent to perform some kind of smoke test.
`python3 -m librelane ./designs/spm/config.json` tests a simple spm design to
ensure nothing has gone horribly wrong.

## Language Standards

### Python

Python code should be written for Python 3.8.1+, and be **typed**. i.e., we
require explicit type annotations for all major API functions.

You will need to ensure that your Python code passes linting with our three
chosen tools:

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
```

Do all arithmetic either in integers or using the Python
[`decimal`](https://docs.python.org/3.6/library/decimal.html) library. All
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

Make your changes and then submit them as a pull requests to the `master`
branch.

Consult [GitHub Help](https://help.github.com/articles/about-pull-requests/) for
more information on using pull requests.

### The Approval Process

For a PR to be merged, there are two requirements:

* There are two automated checks, one for linting and the other for
  functionality. Both must pass.
* An LibreLane team member must inspect and approve the PR.

## Licensing and Copyright

Please note all code contributions must have the same license as LibreLane,
i.e., the Apache License, version 2.0.

For significant changes, please add your (or your employer's) name to the
Authors.md file at the root of the repository.
