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
import dataclasses
import re
import os
import glob
import fnmatch
from enum import Enum
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, Dict, List, Mapping, Sequence, Tuple, Union, Optional

from .variable import Instance, Macro
from ..common import is_string

# https://stackoverflow.com/a/77145529
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

Keys = SimpleNamespace(
    pdk_root="PDK_ROOT",
    pdk="PDK",
    pdkpath="PDKPATH",
    scl="STD_CELL_LIBRARY",
    pad="PAD_CELL_LIBRARY",
    design_dir="DESIGN_DIR",
)

PROCESS_INFO_ALLOWLIST = [
    Keys.pdk,
    Keys.scl,
    Keys.pad,
    f"{Keys.scl}_OPT",
]


Scalar = Union[str, int, Decimal, float, bool, None]
Valid = Union[Scalar, dict, list]


class Expr(object):
    class Token(object):
        class Type(Enum):
            VAR = 0
            NUMBER = 1
            OP = 2
            LPAREN = 3
            RPAREN = 4

        def __init__(self, type: "Expr.Token.Type", value: str) -> None:
            self.type: Expr.Token.Type = type
            self.value: str = value

        def __repr__(self):
            return f"<Token:{self.type} '{self.value}'>"

        def prec_assoc(self) -> Tuple[int, bool]:
            """
            Returns (precedence, is_left_assoc)
            """

            if self.value in ["**"]:
                return (20, False)
            elif self.value in ["*", "/"]:
                return (10, True)
            elif self.value in ["+", "-"]:
                return (0, True)
            else:
                raise TypeError(
                    f"pre-assoc not supported for non-token operators: '{self.value}'"
                )

    @staticmethod
    def tokenize(expr: str) -> List["Expr.Token"]:
        rx_list = [
            (re.compile(r"^\$([A-Za-z_][A-Za-z0-9_\.\[\]]*)"), Expr.Token.Type.VAR),
            (re.compile(r"^(-?\d+\.?\d*)"), Expr.Token.Type.NUMBER),
            (re.compile(r"^(\*\*)"), Expr.Token.Type.OP),
            (re.compile(r"^(\+|\-|\*|\/)"), Expr.Token.Type.OP),
            (re.compile(r"^(\()"), Expr.Token.Type.LPAREN),
            (re.compile(r"^(\))"), Expr.Token.Type.RPAREN),
            (re.compile(r"^\s+"), None),
        ]
        tokens = []
        str_so_far = expr
        while not str_so_far.strip() == "":
            found = False

            for element in rx_list:
                rx, type = element
                m = rx.match(str_so_far)
                if m is None:
                    continue
                found = True
                if type is not None:
                    tokens.append(Expr.Token(type, m[1]))
                str_so_far = str_so_far[len(m[0]) :]
                break

            if not found:
                raise SyntaxError(
                    f"Unexpected token at the start of the following string '{str_so_far}'."
                )
        return tokens

    @staticmethod
    def evaluate(expression: str, symbols: Mapping[str, Any]) -> Decimal:
        tokens: List["Expr.Token"] = Expr.tokenize(expression)
        ETT = Expr.Token.Type

        # Infix to Postfix
        postfix: List["Expr.Token"] = []
        opstack: List["Expr.Token"] = []
        for token in tokens:
            if token.type == ETT.OP:
                prec, assoc = token.prec_assoc()

                top_prec = None
                try:
                    top_prec, _ = opstack[-1].prec_assoc()
                except TypeError:
                    pass
                except IndexError:
                    pass

                while top_prec is not None and (
                    (assoc and prec <= top_prec) or (not assoc and prec < top_prec)
                ):
                    postfix.append(opstack.pop())
                    top_prec = None
                    try:
                        top_prec, _ = opstack[-1].prec_assoc()
                    except IndexError:
                        pass
                opstack.append(token)
            elif token.type == ETT.LPAREN:
                opstack.append(token)
            elif token.type == ETT.RPAREN:
                top = opstack[-1]
                while top.type != ETT.LPAREN:
                    postfix.append(top)
                    opstack.pop()
                    top = opstack[-1]
                opstack.pop()  # drop the LPAREN
            else:
                postfix.append(token)

        while len(opstack):
            postfix.append(opstack[-1])
            opstack.pop()

        # Evaluate
        eval_stack = []
        for token in postfix:
            if token.type == ETT.NUMBER:
                eval_stack.append(Decimal(token.value))
            elif token.type == ETT.VAR:
                try:
                    value = symbols[token.value]
                    if not (
                        isinstance(value, int)
                        or isinstance(value, float)
                        or isinstance(value, Decimal)
                    ):
                        raise TypeError(
                            f"Referenced variable {token.value} is not of a valid numeric type: f{type(value)}"
                        )
                    eval_stack.append(Decimal(value))
                except KeyError:
                    raise TypeError(
                        f"Configuration variable '{token.value}' not found."
                    )
            elif token.type == ETT.OP:
                try:
                    number1 = eval_stack[-2]
                    number2 = eval_stack[-1]
                    eval_stack.pop()
                    eval_stack.pop()

                    result = Decimal("0")
                    if token.value == "**":
                        result = number1**number2
                    elif token.value == "*":
                        result = number1 * number2
                    elif token.value == "/":
                        result = number1 / number2
                    elif token.value == "+":
                        result = number1 + number2
                    elif token.value == "-":
                        result = number1 - number2

                    eval_stack.append(result)
                except IndexError:
                    raise SyntaxError(
                        f"not enough operands for operator '{token.value}'"
                    )

        if len(eval_stack) > 1:
            raise ValueError("expression reduces to multiple values")
        elif len(eval_stack) == 0:
            raise ValueError("expression is empty")

        return eval_stack[0]


ref_rx = re.compile(r"^\$([A-Za-z_][A-Za-z0-9_\.\[\]]*)")


def process_string(
    value: str,
    symbols: Mapping[str, Any],
) -> Valid:
    global ref_rx
    EXPR_PREFIX = "expr::"
    REF_PREFIX = "ref::"
    REFG_PREFIX = "refg::"

    DIR_PREFIX = "dir::"
    PDK_DIR_PREFIX = "pdk_dir::"

    mutable: str = value

    if value.startswith(DIR_PREFIX):
        mutable = value.replace(DIR_PREFIX, f"refg::${Keys.design_dir}/")
    elif value.startswith(PDK_DIR_PREFIX):
        mutable = value.replace(PDK_DIR_PREFIX, f"refg::${Keys.pdkpath}/")

    # before we do anything else, apply inline variable substitution
    mutable = mutable.format(**symbols)

    if mutable.startswith(EXPR_PREFIX):
        try:
            return Expr.evaluate(value[len(EXPR_PREFIX) :], symbols)
        except SyntaxError as e:
            raise SyntaxError(f"Invalid expression '{value}': {e}") from None
    elif mutable.startswith(REF_PREFIX) or mutable.startswith(REFG_PREFIX):
        reference = mutable[mutable.index("::") + 2 :]
        match = ref_rx.match(reference)
        if match is None:
            raise SyntaxError(f"Invalid reference string '{reference}'") from None

        reference_variable = match[1]
        if reference_variable not in symbols:
            raise KeyError(
                f"Referenced variable '{reference_variable}' not found"
            ) from None

        target = symbols[reference_variable]
        if target is None:
            return None

        if not is_string(target):
            if type(target) in [int, float, Decimal]:
                raise TypeError(
                    f"Referenced variable {reference_variable} is a number and not a string: use expr::{match[0]} if you want to reference this number."
                ) from None
            else:
                raise TypeError(
                    f"Referenced variable {reference_variable} is not a valid string: {type(target)}."
                ) from None

        target = str(target)
        concatenated = reference.replace(match[0], target)

        # Glob only if Refg
        if not mutable.startswith(REFG_PREFIX):
            return concatenated

        ## If we're refg, all returns beyond this point must be of type
        ## List[str]
        final_abspath = os.path.abspath(concatenated)

        # Glob only if it doesn't already resolve to a valid file
        if os.path.exists(final_abspath):
            return [final_abspath]

        files = sorted(glob.glob(final_abspath))
        files_escaped = [file.replace("$", r"\$") for file in files]
        files_escaped.sort()

        if len(files_escaped) == 0:
            files_escaped = [concatenated]

        return files_escaped
    else:
        return mutable


PDK_PREFIX = "pdk::"
SCL_PREFIX = "scl::"


def process_list_recursive(
    input: Sequence[Any],
    ref: List[Any],
    symbols: Dict[str, Any],
    *,
    key_path: str = "",
):
    for i, value in enumerate(input):
        current_key_path = f"{key_path}[{i}]"
        processed: Any = None
        if isinstance(value, Mapping):
            processed = {}
            process_dict_recursive(
                value,
                processed,
                symbols,
                key_path=current_key_path,
            )
        elif isinstance(value, Sequence) and not is_string(value):
            processed = []
            process_list_recursive(
                value,
                processed,
                symbols,
                key_path=current_key_path,
            )
        elif is_string(value):
            processed = process_string(value, symbols)
        else:
            processed = value

        if processed is not None:
            ref.append(processed)
            symbols[current_key_path] = processed


def process_dict_recursive(
    input: Mapping[str, Any],
    ref: Dict[str, Any],
    symbols: Dict[str, Any],
    *,
    key_path: str = "",
):
    for key, value in input.items():
        current_key_path = key
        if key_path != "":
            current_key_path = f"{key_path}.{key}"
        processed: Any = None
        if isinstance(value, Mapping):
            if key.startswith(PDK_PREFIX):
                pdk_match = key[len(PDK_PREFIX) :]
                if fnmatch.fnmatch(ref[Keys.pdk], pdk_match):
                    process_dict_recursive(
                        value,
                        ref,
                        symbols,
                        key_path=key_path,
                    )
            elif key.startswith(SCL_PREFIX):
                scl_match = key[len(SCL_PREFIX) :]
                if ref[Keys.scl] is not None and fnmatch.fnmatch(
                    ref[Keys.scl], scl_match
                ):
                    process_dict_recursive(
                        value,
                        ref,
                        symbols,
                        key_path=key_path,
                    )
            else:
                processed = {}
                process_dict_recursive(
                    value,
                    processed,
                    symbols,
                    key_path=current_key_path,
                )

        elif isinstance(value, Sequence) and not is_string(value):
            processed = []
            process_list_recursive(
                value,
                processed,
                symbols,
                key_path=current_key_path,
            )
        elif is_string(value):
            processed = process_string(value, symbols)
        else:
            processed = value

        if not key.startswith(PDK_PREFIX) and not key.startswith(SCL_PREFIX):
            ref[key] = processed
            symbols[current_key_path] = processed


def __coerce_dict(item: Mapping[str, Any] | "DataclassInstance") -> Mapping[str, Any]:
    if dataclasses.is_dataclass(item):
        return dataclasses.asdict(item)
    else:
        return item


def expand_macro_array(
    name_template: str,
    array: Mapping[str, Any],
    orientation: str,
    exposed_variables: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Expands a single macro array.

    Returns a list of macro instantiations.
    """
    out: dict[str, Any] = {}

    # prepare this outside the hot loop
    subs = exposed_variables.copy()

    # initial position
    x, y = array["offset"]
    x_init, y_init = array["offset"]
    x_incr, y_incr = array["step"]
    seq = 0

    rows, cols = array["dimensions"]
    for row in range(rows):
        for col in range(cols):
            # expand the name template, defining the X and Y variables
            subs["X"] = col
            subs["Y"] = row
            # also support row/col syntax
            subs["COL"] = col
            subs["ROW"] = row
            subs["SEQ"] = seq
            # we perform a full preprocess on the string, in case the user has declared other variable names
            # in their macro name, in addition to row/col
            # we also assume that process_string *should* return a string, but to appease mypy, we coax it
            # into being a string here as well
            expanded = str(process_string(name_template, subs))
            out[expanded] = {"location": [x, y], "orientation": orientation}
            x += x_incr
            seq += 1
        # new row, reset
        x = x_init
        y += y_incr

    return out


def locate_and_expand_macro_arrays(
    config_in: Mapping[str, Any],
    exposed_variables: Dict[str, Any],
) -> Mapping[str, Any]:
    """
    Looks for, and expands, macro arrays.

    Returns the config with macro arrays fully expanded.
    """
    out = config_in
    if (macros := config_in.get("MACROS")) is not None:
        for macro_name, macro in macros.items():
            # assume instances must exist
            # we also need to make a copy here, as we're modifying the dictionary as we iterate
            for instance_name, instance in (
                __coerce_dict(macro)["instances"].copy().items()
            ):
                if (array := instance.get("array")) is not None:
                    # perform expansion of this array
                    orientation = __coerce_dict(instance)["orientation"]
                    expansions = expand_macro_array(
                        instance_name,
                        __coerce_dict(array),
                        orientation,
                        exposed_variables,
                    )

                    # add array elements to the root macro instances
                    for expansion_name, expansion in expansions.items():
                        if isinstance(macro, Macro):
                            macro.instances[expansion_name] = Instance(
                                location=expansion["location"],
                                orientation=expansion["orientation"],
                            )
                        else:
                            macro["instances"][expansion_name] = expansion

                    # delete this whole templated instance, since it has now been substituted
                    if isinstance(macro, Macro):
                        del macro.instances[instance_name]
                    else:
                        del macro["instances"][instance_name]
    return out


def process_config_dict(
    config_in: Mapping[str, Any],
    exposed_variables: Dict[str, Any],
) -> Dict[str, Any]:
    state = dict(exposed_variables)
    symbols = dict(exposed_variables)
    # ensure that we expand macro arrays *first*, such that the macro name template is resolved
    expanded = locate_and_expand_macro_arrays(config_in, symbols)
    process_dict_recursive(expanded, state, symbols)
    return state


def extract_process_vars(config_in: Dict[str, str]) -> Dict[str, str]:
    return {
        key: config_in[key]
        for key in PROCESS_INFO_ALLOWLIST
        if config_in.get(key) is not None and config_in.get(key) != ""
    }


def preprocess_dict(
    config_dict: Mapping[str, Any],
    design_dir: str,
    only_extract_process_info: bool = False,
    pdk: Optional[str] = None,
    pdkpath: Optional[str] = None,
    scl: Optional[str] = None,
    pad: Optional[str] = None,
) -> Dict[str, Any]:
    if None in (pdk, pdkpath, scl):
        if only_extract_process_info:
            pdkpath = ""
            scl = ""
            pdk = ""
        else:
            raise TypeError(
                "pdk, pdkpath and scl all need to be non-None unless only_extract_process_info is passed"
            )

    base_vars = {
        Keys.pdk: pdk,
        Keys.pdkpath: pdkpath,
        Keys.scl: scl,
        Keys.pad: pad,
        Keys.design_dir: design_dir,
    }

    preprocessed = process_config_dict(
        config_dict,
        base_vars,
    )
    if only_extract_process_info:
        preprocessed = extract_process_vars(preprocessed)

    return preprocessed
