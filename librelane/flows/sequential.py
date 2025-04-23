# Copyright 2023 Efabless Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import annotations

import os
import fnmatch
from typing import (
    Iterable,
    List,
    Set,
    Tuple,
    Optional,
    Type,
    Dict,
    Union,
)

from rapidfuzz import process, fuzz, utils

from .flow import Flow, FlowException, FlowError
from ..common import Filter
from ..state import State
from ..logging import info, success, debug
from ..steps import (
    Step,
    StepError,
    StepException,
    DeferredStepError,
)

Substitution = Union[str, Type[Step], None]


class SequentialFlow(Flow):
    """
    The simplest Flow, running each Step as a stage, serially,
    with nothing happening in parallel and no significant inter-step
    processing.

    All subclasses of this flow have to do is override the :attr:`.Steps` abstract property
    and it would automatically handle the rest. See `Classic` in Built-in Flows for an example.

    It should be noted, for Steps with duplicate IDs, all Steps other than the
    first one will technically be subclassed with no change other than to simply
    set the ID to the previous step's ID with a suffix: i.e. the second instance
    of ``Test.MyStep`` will have an ID of ``Test.MyStep1``, and so on.

    :param Substitute: Substitute all instances of one `Step` type by another `Step`
        type in the :attr:`.Steps` attribute for this instance only.

        You may also use the string Step IDs in place of a `Step` type object.

        Duplicate ID normalization is re-run after substitutions.

    :param args: Arguments for :class:`Flow`.
    :param kwargs: Keyword arguments for :class:`Flow`.

    :cvar gating_config_vars: A mapping from step ID (wildcards) to lists of
        Boolean variable names. All Boolean variables must be True for a step with
        a specific ID to execute.
    """

    Substitutions: Optional[Dict[str, Union[str, Type[Step], None]]] = None
    gating_config_vars: Dict[str, List[str]] = {}

    def __init_subclass__(Self, scm_type=None, name=None, **kwargs):
        Self.Steps = Self.Steps.copy()  # Break global reference
        Self.config_vars = Self.config_vars.copy()
        Self.gating_config_vars = Self.gating_config_vars.copy()
        if substitute := Self.Substitutions:
            for key, item in substitute.items():
                Self.__substitute_step(Self, key, item)

        Self.__normalize_step_ids(Self)

        # Validate Gating Config Vars
        variables_by_name = {}
        for variable in Self.config_vars:
            variables_by_name[variable.name] = variable

        step_id_set = set()
        for step in Self.Steps:
            step_id_set.add(step.id)

        for id, variable_names in Self.gating_config_vars.items():
            matching_steps = list(Filter([id]).filter(step_id_set))
            if id not in step_id_set and len(matching_steps) < 1:
                continue
            for var_name in variable_names:
                if var_name not in variables_by_name:
                    raise TypeError(
                        f"Gating variable '{var_name}' for Step '{id}' does not match any declared config_vars in Flow '{Self.__qualname__}'"
                    )
                if variables_by_name[var_name].type != bool:
                    raise TypeError(
                        f"Gating variable '{var_name}' in Flow '{Self.__qualname__}' is not a Boolean"
                    )

    @classmethod
    def make(Self, step_ids: List[str]) -> Type[SequentialFlow]:
        Step_list = []
        for name in step_ids:
            step = Step.factory.get(name)
            if step is None:
                raise TypeError(f"No step found with id '{name}'")
            Step_list.append(step)

        class CustomSequentialFlow(SequentialFlow):
            name = "Custom Sequential Flow"
            Steps = Step_list

        return CustomSequentialFlow

    @classmethod
    def Substitute(
        Self, Substitutions: Dict[str, Substitution]
    ) -> Type[SequentialFlow]:
        """
        Convenience method to quickly subclass a sequential flow and add
        Substitutions to it.

        The new flow shall be named ``{previous_flow_name}'``.

        :param Substitutions: The substitutions to use for the new subclass.
        """
        return type(Self.__name__ + "'", (Self,), {"Substitutions": Substitutions})

    def __init__(
        self,
        *args,
        Substitute: Optional[Dict[str, Union[str, Type[Step], None]]] = None,
        **kwargs,
    ):
        self.Steps = self.Steps.copy()  # Break global reference

        if substitute := Substitute:
            for key, item in substitute.items():
                self.__substitute_step(self, key, item)
            self.__normalize_step_ids(self)

        super().__init__(*args, **kwargs)

    @staticmethod
    def __substitute_step(
        target: Union[SequentialFlow, Type[SequentialFlow]],
        id: str,
        with_step: Union[str, Type[Step], None],
    ):
        step_indices: List[int] = []
        mode = "replace"
        if id.startswith("+"):
            id = id[1:]
            mode = "append"
            if with_step is None:
                raise FlowException("Cannot prepend or append None.")
        elif id.startswith("-"):
            id = id[1:]
            mode = "prepend"
            if with_step is None:
                raise FlowException("Cannot prepend or append None.")

        for i, step in enumerate(target.Steps):
            if (
                step.id
                != NotImplemented  # Will be validated later by initialization: ignore for now
                and fnmatch.fnmatch(step.id.lower(), id.lower())
            ):
                step_indices.append(i)
        if len(step_indices) == 0:
            if with_step is None:
                raise FlowException(
                    f"Could not remove '{id}': no steps with ID '{id}' found in flow"
                )
            raise FlowException(
                f"Could not {mode} '{id}' with '{with_step}': no steps with ID '{id}' found in flow."
            )

        if with_step is None:
            for index in reversed(step_indices):
                del target.Steps[index]
            return

        if isinstance(with_step, str):
            with_step_opt = Step.factory.get(with_step)
            if with_step_opt is None:
                raise FlowException(
                    f"Could not {mode} '{id}' with '{with_step}': no replacement step with ID '{with_step}' found."
                )
            with_step = with_step_opt

        for i in step_indices:
            if mode == "replace":
                target.Steps[i] = with_step
            elif mode == "append":
                target.Steps.insert(i + 1, with_step)
            elif mode == "prepend":
                target.Steps.insert(i, with_step)

    @staticmethod
    def __normalize_step_ids(target: Union[SequentialFlow, Type[SequentialFlow]]):
        ids_used: Set[str] = set()

        for i, step in enumerate(target.Steps):
            counter = 0
            id = step.id
            if (
                id == NotImplemented
            ):  # Will be validated later by initialization: ignore for now
                continue
            while id in ids_used:
                counter += 1
                id = f"{step.id}-{counter}"
            if id != step.id:
                target.Steps[i] = step.with_id(id)
            ids_used.add(id)

    def run(
        self,
        initial_state: State,
        frm: Optional[str] = None,
        to: Optional[str] = None,
        skip: Optional[Iterable[str]] = None,
        reproducible: Optional[str] = None,
        **kwargs,
    ) -> Tuple[State, List[Step]]:
        debug(f"Starting run ▶ '{self.run_dir}'")
        step_ids = {cls.id.lower(): cls.id for cls in reversed(self.Steps)}
        skipped_ids: List[str] = []

        def resolve_step(matchable: Optional[str], multiple_ok: bool = False):
            nonlocal step_ids
            dangerous_fuzzy_matching = (
                os.getenv(
                    "_i_want_librelane_to_fuzzy_match_steps_and_im_willing_to_accept_the_risks",
                    None,
                )
                == "1"
            )
            if matchable is None:
                return None
            ids = list(Filter([matchable.lower()]).filter(step_ids))
            if len(ids) > 0:
                if multiple_ok:
                    return [step_ids[id] for id in ids]
                if len(ids) > 1:
                    raise FlowException(f"{matchable} matched multiple steps.")
                if len(ids) == 1:
                    return step_ids[ids[0]]
            else:
                matchTuple = process.extractOne(
                    matchable,
                    step_ids,
                    scorer=fuzz.partial_ratio,
                    score_cutoff=80,
                    processor=utils.default_process,
                )
                suggestion = ""
                if matchTuple is not None:
                    match, _, _ = matchTuple
                    if dangerous_fuzzy_matching:
                        return [match] if multiple_ok else match
                    else:
                        suggestion = f" Did you mean: '{match}'?"
                raise FlowException(
                    f"Failed to process '{matchable}': no step(s) with ID '{matchable}' found in flow.{suggestion}"
                )

        frm_resolved = resolve_step(frm)

        to_resolved = resolve_step(to)

        reproducible_resolved = resolve_step(reproducible)

        if skipped_steps := skip:
            for skipped_step in skipped_steps:
                skipped_ids += resolve_step(skipped_step, multiple_ok=True)

        step_count = len(self.Steps)
        self.progress_bar.set_max_stage_count(step_count)

        step_list = []

        info("Starting…")

        executing = frm is None
        deferred_errors = []

        gating_cvars_expanded: Dict[str, List[str]] = {}
        for key, value in self.gating_config_vars.items():
            if key in step_ids.values():
                gating_cvars_expanded[key] = value
                continue
            for id in Filter([key]).filter(step_ids.values()):
                gating_cvars_expanded[id] = value

        current_state = initial_state
        for cls in self.Steps:
            step = cls(config=self.config, state_in=current_state)
            if frm_resolved is not None and frm_resolved == step.id:
                executing = True

            gated = False
            if gating_cvars := gating_cvars_expanded.get(step.id):
                for variable in gating_cvars:
                    if not self.config[variable]:
                        info(
                            f"Gating variable for step '{step.id}' set to 'False'- the step will be skipped."
                        )
                        gated = True

            self.progress_bar.start_stage(step.name)
            increment_ordinal = True
            if not executing or cls.id in skipped_ids or gated:
                info(f"Skipping step '{step.name}'…")
                increment_ordinal = False
            elif cls.id == reproducible_resolved:
                step.create_reproducible(
                    os.path.join(
                        self.dir_for_step(step),
                        "reproducible",
                    )
                )
                break
            else:
                step_list.append(step)
                try:
                    current_state = step.start(
                        toolbox=self.toolbox,
                        step_dir=self.dir_for_step(step),
                    )
                except StepException as e:
                    raise FlowException(str(e)) from None
                except DeferredStepError as e:
                    deferred_errors.append(str(e))
                except StepError as e:
                    raise FlowError(str(e)) from None

            self.progress_bar.end_stage(increment_ordinal=increment_ordinal)

            if to_resolved and to_resolved == step.id:
                executing = False
        if len(deferred_errors) != 0:
            raise FlowError(
                "One or more deferred errors were encountered:\n"
                + "\n".join(deferred_errors)
            )

        assert self.run_dir is not None
        debug(f"Run concluded ▶ '{self.run_dir}'")
        final_views_path = os.path.join(self.run_dir, "final")
        try:
            current_state.save_snapshot(final_views_path)
        except Exception as e:
            raise FlowException(f"Failed to save final views: {e}")
        success("Flow complete.")
        return (current_state, step_list)
