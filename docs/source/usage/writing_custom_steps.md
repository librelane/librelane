# Writing Custom Steps

Just like you may write custom flows, you may also write custom steps to run
within those flows.

**_Again_**, please review LibreLane's high-level architecture [at this link](../reference/architecture.md).
This defines many of the terms used and enumerates strictures mentioned in this document.

## Generic Steps

Like flows, each Step subclass must:

* Implement the {meth}`librelane.steps.Step.run` method.
  * This step is responsible for the core logic of the step, which is arbitrary.
  * This method must return two values:
    * A `ViewsUpdate`, a dictionary from {class}`DesignFormat` objects to
      Paths for all views altered.
    * A `MetricsUpdate`, a dictionary with valid JSON values.

```{important}
Do NOT call the `run` method of any `Step` from outside of `Step` and its
subclasses- consider it a protected method. `start` is class-independent and
does some incredibly important processing.

You should not be overriding `start` either, which is marked **final**.
```

But also, each Step is required to:

* Declare any required {class}`librelane.state.State` inputs in the `inputs`
  attribute.
  * This will enforce checking the input states for these views.
* Declare any potential state modifications in the `outputs` attribute.
  * This list is checked for completeness and validity- i.e. the {class}`Step`
    superclass WILL throw a `StepException` if a Step modifies any State variable
    it does not declare.
* Declare any used configuration variables in the `config_vars` attribute.

```{important}
Don't forget the [`Step` strictures](#ref-step-strictures). Some of them are
programmatically enforced, but some are still not.
```

### Writing Config Variables

Config variables are declared using the {class}`librelane.config.Variable` object.

There are some conventions to writing these variables.

* Variable names are declared in `UPPER_SNAKE_CASE`, and must be valid
  identifiers in the Python programming language.
* Composite types should be declared using the `typing` module, i.e., for a list
  of strings, try `typing.List[str]` instead of `list[str]` or just `list`.
  * `list[str]` will technically work as of LibreLane 3.0.0, but in older
    versions it did not and even in current versions of Python the type objects
    do not match, i.e. `List[str] != list[str]`. This may cause unexpected bugs.
  * `list` does not give LibreLane adequate information to validate the child
    variables and should not be used under any cirumstance.
* Variables that capture a physical quantity, such as time, distance or similar,
  must declare units using their `"units"` field.
  * In case of micro-, the only SI prefix denoted with a non-Latin letter, use
    this exact Unicode codepoint: `µ`
* Variables may be declared as `pdk`, which determines the compatibility of a
  PDK with your step. If you use a PDK that does not declare one of your
  declared PDK variables, the configuration will not compile and the step will
  raise a {class}`librelane.steps.StepException`.
  * PDK variables should generally avoid having default values other than
    `None`. An exception is when a quantity may be defined by some PDKs, but
    needs a fallback value for others.
* No complex defaults. Defaults must be scalar and quick to evaluate- if your
  default value depends on the default value of another variable, for example,
  set it to `None` and calculate the default value in the step itself.
* All filesystem paths must be declared as {class}`librelane.common.Path`,
  objects which adds some very necessary validation and enables easier
  processing of the variables down the line.
  * Avoid pointing to directories. If your step may require multiple files
    within a directory, try using the type `List[Path]`.

### Implementing `run`

The run header should look like this:

```python
def run(self, state_in: State, *args, **kwargs):
```

The `*args` and `**kwargs` allow subclasses to pass arguments to subprocesses-
more on that later.

You can access configuration variables- which are validated by this point- using
`self.config[KEY]`. If you need to save files, you can get the step directory
using `self.step_dir`. For example:

```python
design_name = self.config["DESIGN_NAME"]
output_path = os.path.join(self.step_dir, f"{design_name}.def")
```

```{note}
A step has access to:

* Its declared `config_vars`
* [All Common Flow Variables](../reference/common_flow_vars.md#universal-flow-configuration-variables)

Attempting to access any other variable is undefined behavior.
```

```{warning}
Ensure that, if your configuration variable is **Optional**, that you explicitly
check if the variable `is not None`. If the variable is not Optional, validation
will handle this check for you.
```

Otherwise, you're basically free to write any logic you desire, with one exception:

* If you're running a terminal subprocess you'd like to have LibreLane manage the
  logs for, please use {meth}`librelane.steps.Step.run_subprocess`,
  passing \*args and \*\*kwargs. It will manage
  I/O for the process, and allow the creation of report files straight from the
  logs- more on that later.

In the end, add any views updated to the first dictionary in the returned tuple,
and any metrics updated to the second dictionary in the returned tuple.

## Creating Reports

You can create report files manually in Python, but if you're running a subprocess,
you can also write `%OL_CREATE_REPORT <name>.rpt` to stdout and everything until
`%OL_END_REPORT` (or another `%OL_CREATE_REPORT`) will be forwarded to a file called
`<name>.rpt` in the step dir automatically.

## Creating Metrics

Likewise, if you're running a subprocess, you can have {meth}`librelane.steps.Step.run_subprocess`
capture them for you automatically by using `%OL_METRIC`. See the documentation
of {meth}`librelane.steps.Step.run_subprocess` for more info.

```{note}
Metrics generated using this method will not be automatically added to the
output state. The {meth}`librelane.steps.Step.run` method is expected to capture
the returned dictionary of any {meth}`librelane.steps.Step.run_subprocess`
invocations and add any values to the returned `MetricUpdate` dictionary as appropriate.
```

## Tool-Specific Steps

The `Step` object makes heavy use of object-oriented programming to encourage
as much code reuse as possible. To that extent, there exists some more specialized
`Step` abstract base classes that deal with specific utilities:

### {class}`librelane.steps.TclStep`

`TclStep` implements a `run` that works for most Tcl-based utilities.
This run calls a subprocess with the value of {meth}`librelane.steps.TclStep.get_command`,
and it emplaces all configuration variables as environment variables using this scheme:

* List variables are joined with a space character.
* Enumerations are replaced with the enumeration name.
* Booleans are replaced with `"1"` if true or `"0"` if false.
* Integers and Decimals are turned into Base-10 strings.

The state is also exposed to the TclStep as is:

* Input files are pointed to in variables with the format `CURRENT_<view name>`.
* Output paths are pointed to in the variables with the format `SAVE_<view name>`.

If a TclStep-based step fails, a reproducible is created, which can be submitted
to the respective repository of the tool.

Keep in mind that TclStep-based tools still have to define their `config_vars`,
`inputs` and `outputs`.

#### Subclasses

`TclStep` has various subclasses for a number of Tcl-based utilities:

* {class}`librelane.steps.OpenROADStep`
* {class}`librelane.steps.YosysStep`
* {class}`librelane.steps.MagicStep`

These subclasses acts as an abstract base class for steps that use their
respective utility. They have one abstract method, `get_script_path`.
Most steps subclassing them might not need to even override `run`.

Additionally, they comes with a common set of `config_vars` required by all invocations
of said tool; you can declare more for your step, however, as shown in this example.:

```python
config_vars = OpenROADStep.config_vars + [
    ...
]
```

Be sure to read the subclasses' `run` docstrings as they may contain critical information.

## While Step

The {class}`librelane.steps.WhileStep` is a specialized step that allows you to execute a sequence of steps repeatedly while a condition is met. This is particularly useful for iterative optimization algorithms or refinement processes.

### Basic Usage

To create a while step, subclass `WhileStep` and define the steps to loop over:

```python
from librelane.steps import WhileStep

class MyIterativeStep(WhileStep):
    id = "MyIterative"
    Steps = [FirstStep, SecondStep, ThirdStep]  # Steps to execute in order
    max_iterations = 10  # Maximum number of iterations
```

The `inputs`, `outputs`, and `config_vars` are automatically generated based on the constituent steps. However, you can explicitly set them if needed.

### Key Attributes

* **`Steps`**: A list of Step classes to execute in each iteration. Required.
* **`max_iterations`**: Maximum number of iterations to run (default: 10).
* **`break_on_failure`**: Whether to stop execution if a step fails (default: True). If False, the loop continues even if a step raises an exception.

### Important Behavior

* **Each iteration starts fresh**: Each iteration always begins with the original input state, not the state from the previous iteration.
* **State persistence**: To carry state across iterations, use the callback functions (see below).

### Callback Functions

`WhileStep` provides several callback functions to customize behavior:

#### `condition(self, state: State) -> bool`

Determines whether to continue iterating. The next iteration will run if the function returns `True`. 

```python
def condition(self, state: State) -> bool:
    # Stop if slack is acceptable
    return state.metrics.get("worst_slack", -999) < -0.5
```

#### `pre_iteration_callback(self, pre_iteration: State) -> State`

Called before each iteration starts. Use this to modify the starting state or prepare for the iteration.

```python
def pre_iteration_callback(self, pre_iteration: State) -> State:
    # Initialize or modify state before iteration
    info(f"Starting iteration with count: {pre_iteration.metrics.get('count', 0)}")
    return pre_iteration
```

#### `mid_iteration_break(self, state: State, step: Step) -> bool`

Called after each individual step within an iteration. If it returns `True`, the current iteration is broken and the next iteration begins immediately. The `post_iteration_callback` is NOT called when breaking mid-iteration. This is useful to stop the iteration early if unfeasible state is found early and stop it to save time.

```python
def mid_iteration_break(self, state: State, step: Step) -> bool:
    # Break if we've reached target after placement
    if step.id == "Placement" and state.metrics.get("target_reached"):
        return True
    return False
```

#### `post_iteration_callback(self, post_iteration: State, full_iter_completed: bool) -> State`

Called after each iteration completes. The `full_iter_completed` parameter indicates whether all steps completed (`True`) or the iteration was broken mid-way (`False`).

```python
def post_iteration_callback(self, post_iteration: State, full_iter_completed: bool) -> State:
    if full_iter_completed:
        # Save the successful iteration state
        self.best_state = post_iteration
    return post_iteration
```

#### `post_loop_callback(self, state: State) -> State`

Called once after all iterations are complete. Use this for final cleanup or processing.

```python
def post_loop_callback(self, state: State) -> State:
    # Restore the best state if we saved one
    if hasattr(self, 'best_state'):
        return self.best_state
    return state
```

### Complete Example

Here's a complete example showing how to use `WhileStep` to iteratively optimize a design:

```python
from librelane.steps import WhileStep, Step
from librelane.state import State

class OptimizationStep(Step):
    id = "Optimize"
    inputs = [DesignFormat.NETLIST]
    outputs = [DesignFormat.NETLIST]
    
    def run(self, state_in: State, **kwargs):
        # Perform optimization
        slack = state_in.metrics.get("worst_slack", -999)
        improved_slack = slack * 0.9  # Simulated improvement
        
        return {}, {"worst_slack": improved_slack}

class IterativeOptimization(WhileStep):
    id = "IterativeOpt"
    Steps = [OptimizationStep]
    max_iterations = 20
    break_on_failure = True
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iteration_count = 0
        self.best_slack = -999
    
    def condition(self, state: State) -> bool:
        """Continue until slack is acceptable"""
        current_slack = state.metrics.get("worst_slack", -999)

        # Stop if slack is good enough
        return current_slack < -0.1
    
    def pre_iteration_callback(self, pre_iteration: State) -> State:
        """Log iteration start"""
        info(f"Starting iteration {self.iteration_count}")

        # update the current worst case for next iteration, 
        # as by default we always start an iteration from the original starting state 
        pre_iteration.metrics["worst_slack"] = self.best_slack
        return pre_iteration
    
    def post_iteration_callback(self, post_iteration: State, full_iter_completed: bool) -> State:
        """Track best result"""
        if full_iter_completed:
            current_slack = post_iteration.metrics.get("worst_slack", -999)
            if current_slack > self.best_slack:
                self.best_slack = current_slack
                info(f"New best slack: {self.best_slack}")
        self.iteration_count += 1
        return post_iteration
    
    def post_loop_callback(self, state: State) -> State:
        """Final reporting"""
        info(f"Optimization complete after {self.iteration_count} iterations")
        info(f"Best slack achieved: {self.best_slack}")
        return state
```
