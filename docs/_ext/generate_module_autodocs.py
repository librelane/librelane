# Copyright 2024 Efabless Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

import importlib
import inspect
import os
import traceback
from types import ModuleType

import jinja2
from docstring_parser import Docstring, parse
from sphinx.application import Sphinx
from sphinx.config import Config
from util import debug, mkdirp, rimraf


def setup(app: Sphinx):
    app.connect("config-inited", generate_module_docs)
    app.add_config_value("generate_module_autodocs", [], True)
    return {"version": "1.0"}


def generate_docs_for_module(
    processed: set[ModuleType],
    build_path: str,
    templates: dict[str, jinja2.Template],
    top_level_name: str | None,
    top_level_dir: str | None,
    module: ModuleType,
    docstring: Docstring,
):
    if module in processed:
        return
    debug(f"Processing {module.__name__}…")
    processed.add(module)

    template = templates["module"]

    assert module.__file__ is not None

    full_name = module.__name__
    module_path = full_name.split(".")
    module_parents = ".".join(module_path[:-1])
    module_name = module_path[-1]

    module_file = os.path.abspath(inspect.getfile(module))

    top_level_name = top_level_name or full_name
    top_level_dir = top_level_dir or os.path.dirname(module_file)

    module_file_rel = os.path.relpath(module_file, top_level_dir)

    if module_file_rel.endswith("__init__.py"):
        module_file_rel = module_file_rel[: -len("__init__.py")]
    elif module_file_rel.endswith(".py"):
        module_file_rel = module_file_rel[:-3]

    module_doc_dir = os.path.abspath(os.path.join(build_path, module_file_rel))
    module_doc_path = os.path.join(module_doc_dir, "index")
    module_rst_path = os.path.join(module_doc_dir, "index.rst")

    submodules = []
    # Process Submodules
    for key in dir(module):
        attr = getattr(module, key)
        try:
            if attr in processed:
                continue
            object_full_name = attr.__name__
            object_path = object_full_name.split(".")
            object_name = object_path[-1]
            object_file = os.path.abspath(inspect.getfile(attr))
        except (TypeError, AttributeError):
            continue

        if not object_file.startswith(top_level_dir):
            continue

        docstring_raw = None
        try:
            docstring_raw = attr.__doc__
        except AttributeError:
            pass

        if docstring_raw is None:
            debug(f"Skipping {object_full_name}: no docstring")
            continue

        object_docstring = parse(docstring_raw)

        if inspect.ismodule(attr):
            submodule = attr
            if submodule.__doc__ is None:
                continue

            submodule_doc_path = generate_docs_for_module(
                processed=processed,
                module=submodule,
                docstring=object_docstring,
                build_path=build_path,
                top_level_name=top_level_name,
                top_level_dir=top_level_dir,
                templates=templates,
            )

            submodule_relative_path = os.path.relpath(
                submodule_doc_path,
                module_doc_dir,
            )

            submodules.append(
                (
                    object_name,
                    object_docstring.short_description,
                    submodule_relative_path,
                )
            )

    short_desc = docstring.short_description
    long_desc = docstring.long_description
    include_imported_members = True
    if "no-imported-members" in long_desc:
        include_imported_members = False

    # Process Current Module
    kwargs = {
        "parent_name": module_parents,
        "full_name": full_name,
        "module_name": module_name,
        "short_desc": short_desc,
        "long_desc": long_desc,
        "submodules": submodules,
        "include_imported_members": include_imported_members,
    }

    mkdirp(os.path.dirname(module_rst_path))
    with open(module_rst_path, "w") as f:
        f.write(template.render(**kwargs))

    return module_doc_path


def generate_module_docs(app: Sphinx, conf: Config):
    try:
        generate_module_autodocs_conf: list[tuple[str, str]] = (
            conf.generate_module_autodocs
        )

        conf_py_path: str = conf._raw_config["__file__"]
        doc_root_dir: str = os.path.dirname(conf_py_path)

        template_relpath: str = conf.templates_path[0]
        all_templates_path = os.path.abspath(template_relpath)
        template_path = os.path.join(all_templates_path, "generate_module_autodocs")

        lookup = jinja2.FileSystemLoader(searchpath=template_path)

        # Mako-like environment
        env = jinja2.Environment(
            "<%",
            "%>",
            "${",
            "}",
            "<%doc>",
            "</%doc>",
            "%",
            "##",
            loader=lookup,
        )

        templates = {k: env.get_template(f"{k}.rst") for k in ["module"]}
        for module_name, build_path in generate_module_autodocs_conf:
            rimraf(build_path)

            build_path_resolved = os.path.join(doc_root_dir, build_path)
            top_level_module = importlib.import_module(module_name)

            try:
                docstring_raw = top_level_module.__doc__
            except AttributeError:
                raise ValueError("Top level module lacks a docstring.")

            docstring = parse(docstring_raw)

            generate_docs_for_module(
                processed=set(),
                module=top_level_module,
                docstring=docstring,
                build_path=build_path_resolved,
                templates=templates,
                top_level_name=None,
                top_level_dir=None,
            )
    except Exception:
        print(traceback.format_exc())
        exit(-1)
