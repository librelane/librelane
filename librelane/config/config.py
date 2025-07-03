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
import os
import json
import yaml
from yamlcore import CCoreLoader
import dataclasses
from glob import glob
from decimal import Decimal
from textwrap import dedent
from functools import lru_cache
from dataclasses import dataclass
from typing import (
    Any,
    ClassVar,
    Literal,
    Mapping,
    Tuple,
    Union,
    List,
    Optional,
    Sequence,
    Dict,
    Set,
)

from .variable import Variable, MissingRequiredVariable
from .removals import removed_variables
from .flow import pdk_variables, scl_variables, flow_common_variables
from .pdk_compat import migrate_old_config
from .preprocessor import preprocess_dict, Keys as SpecialKeys
from ..logging import info, warn
from ..__version__ import __version__
from ..common import (
    GenericDict,
    GenericImmutableDict,
    TclUtils,
    AnyPath,
    is_string,
)

AnyConfig = Union[AnyPath, Mapping[str, Any]]
AnyConfigs = Union[AnyConfig, Sequence[AnyConfig]]


class _OpenLaneYAMLLoader(CCoreLoader):
    def construct_yaml_float(self, node: yaml.ScalarNode) -> Decimal:  # type: ignore
        value = str(self.construct_scalar(node))
        value = value.replace("_", "").lower()
        sign = +1
        if value[0] == "-":
            sign = -1
        if value[0] in "+-":
            value = value[1:]
        if value == ".inf":
            return sign * Decimal("Infinity")
        elif value == ".nan":
            return Decimal("nan")
        else:
            return sign * Decimal(value)

    def __init__(self, stream) -> None:
        super().__init__(stream)
        self.add_constructor(
            "tag:yaml.org,2002:float",
            constructor=_OpenLaneYAMLLoader.construct_yaml_float,
        )
        # print(list(self.yaml_implicit_resolvers.keys()))
        # del self.yaml_implicit_resolvers["tag:yaml.org,2002:float"]


class UnknownExtensionError(ValueError):
    """
    When a passed configuration file has an unrecognized extension, i.e.,
    not .json, .yml/.yaml or .tcl.
    """

    def __init__(self, config: AnyPath) -> None:
        self.config = str(config)
        _, ext = os.path.splitext(config)
        super().__init__(
            f"Unsupported configuration file extension '{ext}' for '{config}'."
        )


class PassedDirectoryError(ValueError):
    """
    When a passed configuration file is in fact a directory.
    """

    def __init__(self, config: AnyPath) -> None:
        self.config = str(config)
        super().__init__(
            "Passing design directories as arguments is unsupported in LibreLane: please pass the configuration file(s) directly."
        )


def _validate_config_file(config: AnyPath) -> Literal["json", "tcl", "yaml"]:
    config = str(config)
    if config.endswith(".tcl"):
        return "tcl"
    elif config.endswith(".json"):
        return "json"
    elif config.endswith(".yml") or config.endswith(".yaml"):
        return "yaml"
    elif os.path.isdir(config):
        raise PassedDirectoryError(config)
    else:
        raise UnknownExtensionError(config)


class InvalidConfig(ValueError):
    """
    An error raised when a configuration under resolution is invalid.

    :param config: A human-readable name for the particular configuration file
        causing this exception, i.e. whether it's a PDK configuration file or a
        user configuration file.
    :param warnings: A list of warnings generated during the loading of this
        configuration file.
    :param errors: A list of errors generated during the loading of this
        configuration file.
    :param args: Further arguments to be passed onto the constructor of
        :class:`ValueError`.
    :param message: An optional override for the Exception message.
    :param kwargs: Further keyword arguments to be passed onto the constructor of
        :class:`ValueError`.
    """

    def __init__(
        self,
        config: str,
        warnings: List[str],
        errors: List[str],
        message: Optional[str] = None,
        *args,
        **kwargs,
    ) -> None:
        self.config = config
        self.warnings = warnings
        self.errors = errors
        if message is None:
            message = "The following errors were encountered: \n"
            for error in self.errors:
                message += f"\t* {error}\n"
            message = message.strip()
        super().__init__(message, *args, **kwargs)


@dataclass
class Meta:
    """
    Constitutes metadata for a configuration object.
    """

    version: int = 1
    flow: Union[None, str, List[str]] = None
    substituting_steps: Union[None, Dict[str, Union[str, None]]] = None
    step: Union[None, str] = None
    librelane_version: Union[None, str] = __version__

    @classmethod
    def from_dict(Self, meta_dict: dict):
        meta_dict_copy = meta_dict.copy()
        if "openlane_version" in meta_dict_copy:
            meta_dict_copy["librelane_version"] = meta_dict_copy["openlane_version"]
            del meta_dict_copy["openlane_version"]
        return Self(**meta_dict_copy)

    def copy(self) -> "Meta":
        return dataclasses.replace(self)


class Config(GenericImmutableDict[str, Any]):
    """
    A map from LibreLane configuration variable keys to their values.

    It is recommended that you use :meth:`load` to create new, validated
    configurations from dictionaries or files.

    :param meta: The :class:`Meta` object for this configuration. If ``None`` is
        passed, the default Meta object will be assigned.
    :param final: Whether the configuration is final (i.e. has been
        pre-assembled for an entire flow) or may be incremented per-step.

        Final configurations may not be adjusted or incremented.

    """

    current_interactive: ClassVar[Optional["Config"]] = None
    meta: Meta

    def __init__(
        self,
        *args,
        meta: Optional[Meta] = None,
        **kwargs,
    ):
        if meta is None:
            meta = Meta(version=1)

        self.meta = meta

        super().__init__(*args, **kwargs)

    def copy(self, **overrides) -> "Config":
        """
        Produces a *shallow* copy of the configuration object.

        :param overrides: A series of configuration overrides as key-value pairs.
            These values are NOT validated and you should not be overriding these
            haphazardly.
        """
        return Config(self, meta=self.meta, overrides=overrides)

    def to_raw_dict(self, include_meta: bool = True) -> Dict[str, Any]:
        """
        :param include_meta: Whether to include the "meta" object or not
        :returns: A raw dictionary representation including the ``meta`` object.
        """
        final = super().to_raw_dict()
        if include_meta:
            final["meta"] = self.meta
        return final

    def dumps(self, include_meta: bool = True, **kwargs) -> str:
        """
        :param include_meta: Whether to include the ``meta`` object in the
            serialized string.
        :param kwargs: Passed to ``json.dumps``.
        :returns: A JSON string representing the the GenericDict object.
        """
        if "indent" not in kwargs:
            kwargs["indent"] = 4
        return json.dumps(
            self.to_raw_dict(include_meta), cls=self.get_encoder(), **kwargs
        )

    def copy_filtered(
        self,
        config_vars: Sequence[Variable],
        include_flow_variables: bool = True,
    ) -> "Config":
        """
        Creates a new copy of the configuration object, but only with the
        configuration variables defined by the parameter.

        :param config_vars: A list of configuration variables to include in
            the filtered copy.
        :param include_flow_variables: Whether to include the common flow
            variables in the copy or not.

            This parameter is deprecated as of LibreLane 2.0.0b5 and should be
            set to ``False`` by callers.
        :returns: The new copy
        """
        variables: Set[str] = set([variable.name for variable in config_vars])
        if include_flow_variables:
            variables = variables.union(
                set([variable.name for variable in flow_common_variables])
            )

        return Config(
            {variable: self[variable] for variable in variables},
            meta=dataclasses.replace(self.meta),
        )

    def with_increment(
        self,
        config_vars: Sequence[Variable],
        other_inputs: Mapping[str, Any],
        config_quiet: bool = False,
    ) -> "Config":
        """
        Creates a new ``Config`` object by copying all values
        from the original in addition to any new variables (and removing
        any variables not in `config_vars`).

        Furthermore, inputs can be provided incrementally by passing the object
        ``other_inputs``, which will also use these as overrides to the
        values in the base ``Config`` object.

        All values, including those in the base ``Config`` object and in
        ``other_inputs``, will be re-validated.

        :param config_vars: A list of configuration variables to include and
            validate.
        :param other_inputs: A mapping of other inputs.
        :returns: The new ``Config`` object
        """
        incremental_pdk_vars = [variable for variable in config_vars if variable.pdk]

        mutable, _, _ = self.__get_pdk_config(
            self["PDK"],
            self["STD_CELL_LIBRARY"],
            self["PDK_ROOT"],
            incremental_pdk_vars,
        )

        mutable.update(self)
        mutable.update(other_inputs)

        processed, design_warnings, design_errors = Config.__process_variable_list(
            mutable,
            config_vars,
            removed_variables,
            on_unknown_key=None,
        )

        if len(design_errors) != 0:
            raise InvalidConfig(
                "incremental configuration", design_warnings, design_errors
            )

        if not config_quiet:
            if len(design_warnings) > 0:
                info(
                    "Loading the incremental configuration has generated the following warnings:"
                )
            for warning in design_warnings:
                warn(warning)

        return Config(
            processed,
            meta=self.meta.copy(),
        )

    @classmethod
    def get_meta(
        Self,
        config_in: AnyConfig,
        flow_override: Optional[str] = None,
    ) -> Meta:
        """
        Returns the Meta object of a configuration dictionary or file.

        :param config_in: A configuration object or file.
        :returns: Either a Meta object, or if the file is invalid, None.
        """
        default_meta_version = 2

        if is_string(config_in):
            config_in = str(config_in)
            validated_type = _validate_config_file(config_in)
            if validated_type == "tcl":
                default_meta_version = 1
                return Meta(version=default_meta_version)
            elif validated_type == "json":
                default_meta_version = 1
                config_in = json.load(open(config_in, encoding="utf8"))
            elif validated_type == "yaml":
                config_in = yaml.load(
                    open(config_in, encoding="utf8"),
                    Loader=_OpenLaneYAMLLoader,
                )

        assert not isinstance(config_in, str)
        assert not isinstance(config_in, os.PathLike)

        meta = Meta(version=default_meta_version)
        if meta_raw := config_in.get("meta"):
            meta = Meta.from_dict(meta_raw)

        if flow_override is not None:
            meta.flow = flow_override

        return meta

    @classmethod
    def interactive(
        Self,
        DESIGN_NAME: str,
        PDK: str,
        STD_CELL_LIBRARY: Optional[str] = None,
        PDK_ROOT: Optional[str] = None,
        **kwargs,
    ) -> "Config":
        """
        This constructs a partial configuration object that may be incrementally
        adjusted per-step, and activates LibreLane's **interactive mode**.

        The interactive mode is overall less rigid than the pure mode, adding various
        references to global objects to make the REPL or Notebook experience more
        pleasant, however, it is not as resilient as the pure mode and should not
        be used in production code.

        :param DESIGN_NAME: The name of the design to be used.
        :param PDK: The name of the PDK.
        :param STD_CELL_LIBRARY: The name of the standard cell library.

            If not specified, the PDK's default SCL will be used.
        :param PDK_ROOT: Required if Volare is not installed.

            If Volare is installed, this value can be used to optionally override
            Volare's default.

        :param kwargs: Any overrides to PDK values and/or common flow default variables
            can be passed as keyword arguments to this function.

            Useful examples are CLOCK_PORT, CLOCK_PERIOD, et cetera, which while
            not bound to a specific :class:`Step`, affects most Steps' behavior.
        """
        PDK_ROOT = Self.__resolve_pdk_root(PDK_ROOT)

        raw, _, _ = Self.__get_pdk_config(
            PDK,
            STD_CELL_LIBRARY,
            PDK_ROOT,
            pdk_variables + scl_variables,
        )

        kwargs["DESIGN_NAME"] = DESIGN_NAME
        kwargs["DESIGN_DIR"] = kwargs.get("DESIGN_DIR", ".")

        raw.update(kwargs)

        processed, design_warnings, design_errors = Config.__process_variable_list(
            raw,
            flow_common_variables,
            removed_variables,
            on_unknown_key="error",
        )

        if len(design_errors) != 0:
            raise InvalidConfig("default configuration", design_warnings, design_errors)

        if len(design_warnings) > 0:
            info(
                "Loading the default configuration has generated the following warnings:"
            )
        for warning in design_warnings:
            warn(warning)

        Config.current_interactive = Config(processed)

        return Config.current_interactive

    @classmethod
    def load(
        Self,
        config_in: AnyConfigs,
        flow_config_vars: Sequence[Variable],
        *,
        config_override_strings: Optional[Sequence[str]] = None,
        pdk: Optional[str] = None,
        pdk_root: Optional[str] = None,
        scl: Optional[str] = None,
        design_dir: Optional[str] = None,
        _load_pdk_configs: bool = True,
    ) -> Tuple["Config", str]:
        """
        Creates a new Config object based on a Tcl file, a JSON file, or a
        dictionary.

        The returned config object is locked and cannot be modified.

        :param config_in: Either a file path to a JSON file or a Python
            Mapping object (such as ``dict``) representing an unprocessed
            LibreLane configuration object.

            Tcl files are also supported, but are deprecated and will be removed
            in the future.

        :param config_override_strings: A list of "overrides" in the form of
            NAME=VALUE strings. These are primarily for running LibreLane from
            the command-line and strictly speaking should not be used in the API.

        :param design_dir: The design directory for said configuration(s).

            If not explicitly provided, the design directory will be the
            directory holding the last file in the list.

            If no files are provided, this argument is required.

        :param pdk: A process design kit to use. Required unless specified via the
            "PDK" key in a configuration object.

        :param pdk_root: Required if Volare is not installed.

            If Volare is installed, this value can be used to optionally override
            Volare's default.

        :param scl: A standard cell library to use. If not specified, the PDK's
            default standard cell library will be used instead.

        :returns: A tuple containing a Config object and the design directory.
        """
        if isinstance(config_in, Mapping):
            config_in = [config_in]
        elif is_string(config_in):
            config_in = [str(config_in)]

        assert not isinstance(config_in, str)
        assert not isinstance(config_in, os.PathLike)

        if len(config_in) == 0:
            raise ValueError("The value for config_in must not be empty.")

        file_design_dir = None
        configs_validated: List[AnyConfig] = []
        for config in config_in:
            if isinstance(config, Mapping):
                configs_validated.append(config)
            # Path
            else:
                config = str(config)
                _validate_config_file(config)
                config_abspath = os.path.abspath(config)
                file_design_dir = os.path.dirname(config_abspath)
                configs_validated.append(config_abspath)

        design_dir = design_dir or file_design_dir
        if design_dir is None:
            raise ValueError(
                "The design_dir argument is required when configuration dictionaries are used."
            )

        config_obj = Config()
        for config_validated in configs_validated:
            try:
                meta = Self.get_meta(config_validated)
            except TypeError as e:
                identifier = "configuration dict"
                if is_string(config_validated):
                    identifier = os.path.relpath(str(config_validated))
                raise InvalidConfig(identifier, [], [f"'meta' object is invalid: {e}"])

            mapping = None
            if isinstance(config_validated, Mapping):
                mapping = config_validated
            elif isinstance(config_validated, str):
                validated_type = _validate_config_file(config_validated)
                if validated_type == "tcl":
                    mapping = Self.__mapping_from_tcl(
                        config_validated,
                        design_dir,
                        pdk_root=pdk_root,
                        pdk=pdk,
                        scl=scl,
                    )
                elif validated_type == "json":
                    mapping = json.load(
                        open(config_validated, encoding="utf8"),
                        parse_float=Decimal,
                    )
                elif validated_type == "yaml":
                    mapping = yaml.load(
                        open(config_validated, encoding="utf8"),
                        Loader=_OpenLaneYAMLLoader,
                    )

            assert mapping is not None, "Invalid validated config"

            mutable = config_obj.copy_mut()
            mutable.update_reorder(mapping)
            config_obj = Self.__load_dict(
                mutable,
                design_dir,
                flow_config_vars=flow_config_vars,
                pdk_root=pdk_root,
                pdk=pdk,
                scl=scl,
                meta=meta,
                permissive_typing=meta.version < 2,
                missing_ok=True,
                _load_pdk_configs=_load_pdk_configs,
            )

            _load_pdk_configs = False  # one time's enough

        # Final signoff + override strings
        config_override_strings = config_override_strings or []
        mutable = config_obj.copy_mut()
        for string in config_override_strings:
            key, value = string.split("=", 1)
            mutable[key] = value

        config_obj = Self.__load_dict(
            mutable,
            design_dir,
            flow_config_vars=flow_config_vars,
            pdk_root=pdk_root,
            pdk=pdk,
            scl=scl,
            meta=config_obj.meta,  # carry forward
            missing_ok=False,  # must all exist
            permissive_typing=True,  # so we can parse things from the commandline
            _load_pdk_configs=False,  # one time's enough
        )

        return (config_obj, design_dir)

    ## For Jupyter
    def _repr_markdown_(self) -> str:  # pragma: no cover
        title = (
            "Interactive Configuration"
            if self == Config.current_interactive
            else "Configuration"
        )
        values_title = (
            "Initial Values" if self == Config.current_interactive else "Values"
        )
        return (
            dedent(
                f"""
                ### {title}
                #### {values_title}

                <br />

                ```yaml
                %s
                ```
                """
            )
            % yaml.safe_dump(json.loads(self.dumps()))
        )

    ## Private Methods
    @classmethod
    def __load_dict(
        Self,
        mapping_in: Mapping[str, Any],
        design_dir: str,
        flow_config_vars: Sequence[Variable],
        *,
        meta: Meta,
        pdk_root: Optional[str] = None,
        pdk: Optional[str] = None,
        scl: Optional[str] = None,
        full_pdk_warnings: bool = False,
        permissive_typing: bool = False,
        missing_ok: bool = False,
        _load_pdk_configs: bool = True,
    ) -> "Config":
        raw = dict(mapping_in)

        if "meta" in raw:
            del raw["meta"]

        flow_option_vars = []
        flow_pdk_vars = []
        for variable in flow_config_vars:
            if variable.pdk:
                flow_pdk_vars.append(variable)
            else:
                flow_option_vars.append(variable)

        mutable = GenericDict(
            preprocess_dict(
                raw,
                only_extract_process_info=True,
                design_dir=design_dir,
            )
        )

        pdk = mutable.get(SpecialKeys.pdk) or pdk
        scl = mutable.get(SpecialKeys.scl) or scl
        pdkpath = ""

        mutable["PDK_ROOT"] = pdk_root

        if _load_pdk_configs:
            pdk_root = Self.__resolve_pdk_root(pdk_root)
            if pdk is None:
                raise ValueError(
                    "The pdk argument is required as the configuration object lacks a 'PDK' key."
                )

            mutable, pdkpath, scl = Self.__get_pdk_config(
                pdk=pdk,
                scl=scl,
                pdk_root=pdk_root,
                full_pdk_warnings=full_pdk_warnings,
                flow_pdk_vars=flow_pdk_vars,
            )
        else:
            if pdk_root is not None:
                pdkpath = os.path.join(pdk_root, mutable["PDK"])

        readable_paths = [
            os.path.abspath(design_dir),
        ]
        if pdkpath != "":
            readable_paths.append(os.path.abspath(pdkpath))

        mutable.update(
            preprocess_dict(
                raw,
                pdk=pdk,
                pdkpath=pdkpath,
                scl=mutable[SpecialKeys.scl],
                design_dir=design_dir,
                readable_paths=readable_paths,
            )
        )

        processed, design_warnings, design_errors = Config.__process_variable_list(
            mutable,
            list(flow_config_vars),
            removed_variables,
            missing_ok=missing_ok,
            permissive_typing=permissive_typing,
            on_unknown_key="warn" if permissive_typing else "error",
        )

        if len(design_errors) != 0:
            raise InvalidConfig(
                "design configuration file", design_warnings, design_errors
            )

        if len(design_warnings) > 0:
            info(
                "Loading the design configuration file has generated the following warnings:"
            )
        for warning in design_warnings:
            warn(warning)

        return Config(processed, meta=meta)

    @classmethod
    def __mapping_from_tcl(
        Self,
        config: AnyPath,
        design_dir: str,
        *,
        pdk_root: Optional[str] = None,
        pdk: Optional[str] = None,
        scl: Optional[str] = None,
    ) -> Mapping[str, Any]:
        config_str = open(config, encoding="utf8").read()

        warn(
            "Support for .tcl configuration files is deprecated. Please migrate to a .json file at your earliest convenience."
        )

        pdk_root = Self.__resolve_pdk_root(pdk_root)

        tcl_vars_in = GenericDict(
            {
                SpecialKeys.pdk_root: pdk_root,
                SpecialKeys.pdk: pdk,
            }
        )
        tcl_vars_in[SpecialKeys.scl] = ""
        tcl_vars_in[SpecialKeys.design_dir] = design_dir
        tcl_config = GenericDict(TclUtils._eval_env(tcl_vars_in, config_str))

        process_info = preprocess_dict(
            tcl_config,
            only_extract_process_info=True,
            design_dir=design_dir,
        )

        pdk = process_info.get(SpecialKeys.pdk) or pdk

        if pdk is None:
            raise ValueError(
                "The pdk argument is required as the configuration object lacks a 'PDK' key."
            )

        _, _, scl = Self.__get_pdk_config(
            pdk=pdk,
            scl=scl,
            pdk_root=pdk_root,
            full_pdk_warnings=False,
        )

        tcl_vars_in[SpecialKeys.pdk] = pdk
        tcl_vars_in[SpecialKeys.scl] = scl
        tcl_vars_in[SpecialKeys.design_dir] = design_dir

        tcl_mapping = GenericDict(TclUtils._eval_env(tcl_vars_in, config_str))

        return tcl_mapping

    @classmethod
    def __resolve_pdk_root(
        Self,
        pdk_root: Optional[str],
    ) -> str:
        if pdk_root is None:
            try:
                import ciel

                pdk_root = ciel.get_ciel_home(pdk_root)
            except ImportError:
                raise ValueError(
                    "The pdk_root argument is required as Ciel is not installed."
                )

        return os.path.abspath(pdk_root)

    @staticmethod
    @lru_cache(1, True)
    def __get_pdk_raw(
        pdk_root: str, pdk: str, scl: Optional[str]
    ) -> Tuple[GenericImmutableDict[str, Any], str, str]:
        pdk_config: GenericDict[str, Any] = GenericDict(
            {
                SpecialKeys.pdk_root: pdk_root,
                SpecialKeys.pdk: pdk,
            }
        )

        if scl is not None:
            pdk_config[SpecialKeys.scl] = scl

        pdkpath = os.path.join(pdk_root, pdk)
        if not os.path.exists(pdkpath):
            matches = sorted(glob(f"{pdkpath}*"))
            errors = [f"The PDK {pdk} was not found."]
            warnings = []
            for match in matches:
                basename = os.path.basename(match)
                warnings.append(f"A similarly-named PDK was found: {basename}")
            raise InvalidConfig("PDK configuration", warnings, errors)

        pdk_config_path = os.path.join(pdkpath, "libs.tech", "librelane", "config.tcl")
        if not os.path.exists(pdk_config_path):
            pdk_config_path_alt = os.path.join(
                pdkpath, "libs.tech", "openlane", "config.tcl"
            )
            if not os.path.exists(pdk_config_path_alt):
                raise InvalidConfig(
                    "PDk configuration",
                    [],
                    [
                        f"Neither '{pdk_config_path}' nor '{pdk_config_path_alt} were found.'"
                    ],
                )
            pdk_config_path = pdk_config_path_alt

        pdk_env = TclUtils._eval_env(
            pdk_config,
            open(pdk_config_path, encoding="utf8").read(),
        )

        scl = pdk_env["STD_CELL_LIBRARY"]
        assert (
            scl is not None
        ), "Fatal error: STD_CELL_LIBRARY default value not set by PDK."

        scl_config_path = os.path.join(
            pdkpath, "libs.tech", "librelane", scl, "config.tcl"
        )
        if not os.path.exists(scl_config_path):
            scl_config_path_alt = os.path.join(
                pdkpath, "libs.tech", "openlane", scl, "config.tcl"
            )
            if not os.path.exists(scl_config_path_alt):
                raise InvalidConfig(
                    "PDk configuration",
                    [],
                    [
                        f"Neither '{scl_config_path}' nor '{scl_config_path_alt} were found.'"
                    ],
                )
            scl_config_path = scl_config_path_alt

        scl_env = migrate_old_config(
            TclUtils._eval_env(
                pdk_env,
                open(scl_config_path, encoding="utf8").read(),
            )
        )

        return GenericImmutableDict(scl_env), pdkpath, scl

    @staticmethod
    def __get_pdk_config(
        pdk: str,
        scl: Optional[str],
        pdk_root: str,
        flow_pdk_vars: Optional[List[Variable]] = None,
        full_pdk_warnings: Optional[bool] = False,
    ) -> Tuple[GenericDict[str, Any], str, str]:
        """
        :returns: A tuple of the PDK configuration, the PDK path and the SCL.
        """

        frozen, pdkpath, scl = Config.__get_pdk_raw(pdk_root, pdk, scl)
        if flow_pdk_vars is None or len(flow_pdk_vars) == 0:
            return (GenericDict(), pdkpath, scl)

        raw: GenericDict[str, Any] = GenericDict(frozen)  # microwave
        processed, pdk_warnings, pdk_errors = Config.__process_variable_list(
            raw,
            flow_pdk_vars,
            on_unknown_key=None,
            permissive_typing=True,
        )

        if len(pdk_errors) != 0:
            raise InvalidConfig("PDK configuration files", pdk_warnings, pdk_errors)

        if len(pdk_warnings) > 0:
            if full_pdk_warnings:
                info(
                    "Loading the PDK configuration files has generated the following warnings:"
                )
                for warning in pdk_warnings:
                    warn(warning)

        processed["PDK_ROOT"] = pdk_root
        processed["PDK"] = pdk

        return (processed, pdkpath, scl)

    def __process_variable_list(
        mutable: GenericDict[str, Any],
        variables: Sequence["Variable"],
        removed: Optional[Mapping[str, str]] = None,
        *,
        on_unknown_key: Union[Literal["error", "warn"], None] = "warn",
        permissive_typing: bool = False,
        missing_ok: bool = False,
    ) -> Tuple[GenericDict[str, Any], List[str], List[str]]:
        """
        Verifies a configuration object against a list of variables, returning
        an object with the variables normalized according to their types.

        :param config: The input, raw configuration object.
        :param variables: A sequence or some other iterable of variables.
        :param removed: A dictionary of variables that may have existed at a point in
            time, but then have gotten removed. Useful to give feedback to the user.
        :returns: A tuple of:
            [0] A final, processed configuration.
            [1] A list of warnings.
            [2] A list of errors.

            If the third element is non-empty, the first object is invalid.
        """
        if removed is None:
            removed = {}
        warnings: List[str] = []
        errors = []
        final: GenericDict[str, Any] = GenericDict()

        # Special Deprecation Behaviors
        if (
            mutable.get("DIODE_INSERTION_STRATEGY") is not None
        ):  # Can't use := because 0 is a valid value
            dis = mutable["DIODE_INSERTION_STRATEGY"]
            del mutable["DIODE_INSERTION_STRATEGY"]
            try:
                dis = int(dis)
            except ValueError:
                pass
            if not isinstance(dis, int) or dis in [1, 2, 5] or dis > 6:
                errors.append(
                    f"DIODE_INSERTION_STRATEGY '{dis}' is not available in LibreLane 2.0 or higher. See 'Migrating DIODE_INSERTION_STRATEGY' in the docs for more info."
                )
            else:
                warnings.append(
                    "The DIODE_INSERTION_STRATEGY variable has been deprecated. See 'Migrating DIODE_INSERTION_STRATEGY' in the docs for more info."
                )

                mutable["GRT_REPAIR_ANTENNAS"] = False
                mutable["RUN_HEURISTIC_DIODE_INSERTION"] = False
                mutable["DIODE_ON_PORTS"] = "none"
                if dis in [3, 6]:
                    mutable["GRT_REPAIR_ANTENNAS"] = True
                if dis in [4, 6]:
                    mutable["RUN_HEURISTIC_DIODE_INSERTION"] = True
                    mutable["DIODE_ON_PORTS"] = "in"

        for variable in variables:
            try:
                key, value_processed = variable.compile(
                    mutable_config=mutable,
                    warning_list_ref=warnings,
                    values_so_far=final,
                    permissive_typing=permissive_typing,
                )
                if key is not None:
                    del mutable[key]
                final[variable.name] = value_processed
            except MissingRequiredVariable as e:
                if not missing_ok:
                    errors.append(str(e))
            except ValueError as e:
                errors.append(str(e))
            if variable.name in mutable:
                del mutable[variable.name]

        for key in sorted(mutable.keys()):
            assert isinstance(key, str)

            if key in vars(SpecialKeys).values():
                continue
            if key in removed:
                warnings.append(f"'{key}' has been removed: {removed[key]}")
            elif (
                "_OPT" not in key
                and not key.startswith("//")
                and not key.startswith("#")
            ):
                if on_unknown_key == "error":
                    if key in Variable.known_variable_names:
                        warnings.append(
                            f"Key '{key}' provided is unused by the current flow."
                        )
                    else:
                        errors.append(f"Unknown key '{key}' provided.")
                elif on_unknown_key == "warn":
                    if key in Variable.known_variable_names:
                        warnings.append(
                            f"Key '{key}' provided is unused by the current flow."
                        )
                    else:
                        warnings.append(f"An unknown key '{key}' was provided.")

        return (final, warnings, errors)
