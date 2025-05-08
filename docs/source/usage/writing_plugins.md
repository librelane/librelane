# Writing and Using Plugins

LibreLane plugin modules are written in Python and can be added to `PYTHONPATH`
or installed to your Python `site-packages` (e.g. installed either inside
or outside a venv). LibreLane detects and imports all Python modules found that
have the prefix `librelane_plugin_`.

Plugins are useful to add support for more utilities other than those included
with LibreLane; either alternative open-source EDA utilities that are not part of
the built-in flows, or proprietary utilities that can never be a part of the
built-in parts.

```{note}
Plugins are not supported in LibreLane Docker containers.
```

## Registering new Flows and Steps

Plugins, much like LibreLane itself, may create and register steps and flows into
global registries, where the steps and flows can then be accessed
programmatically via their ID.

You can use the Python decorators `@Flow.factory.register()` and
`@Step.factory.register()` to register flows and steps respectively.

Registered flows and steps can be accessed in configuration files as shown in
{doc}`/usage/writing_custom_flows`, but they can also be accessed
programmatically as follows:

```python
MyCustomStep = Step.factory.get("ToolName.MyCustomStep")
MyCustomFlow = Flow.factory.get("MyCustomFlow")
```

For information on writing the flows and steps themselves, see
{doc}`/usage/writing_custom_flows` and {doc}`/usage/writing_custom_steps`.

## Including Tools

Naturally, one of the most important uses of plugins is the ability to write
steps for other tools. There are multiple ways to include these tools:

### Bring-your-own-tools

You may require users to bring their own tools by installing them on their own
and adding them to `PATH`, then running LibreLane with the plugin separately.

This is usually the only option for proprietary utilities.

You can still install the plugin itself with Nix while requiring the tool be
separate- see the section below.

### With Nix

```{note}
This section requires a strong understanding of the Nix programming language,
including the Flakes feature, to follow.
```

You may bundle either the plugin alone or the plugin and the tool using Nix.

The flake for LibreLane contains a function named `createOpenLaneShell` in its 
outputs. This creates a [devshell](https://github.com/numtide/devshell), which
is an executable script that drops you into an environment with LibreLane, its
dependencies, and optionally plugins, installed.

The plugins are to be regular Python Nix derivations, built using the
[`buildPythonPackage` function](https://github.com/NixOS/nixpkgs/blob/master/doc/languages-frameworks/python.section.md#buildpythonpackage-function-buildpythonpackage-function)
with one addition: Plugins must have the attribute `includedTools`, declaring
tool dependencies (so they may be available to the user standalone in the
environment).

For example, if a plugin, for some reason, depends on the Python `numpy` library
and incorporates `bash`, it can declare its dependencies as follows:

```nix
  propagatedBuildInputs = includedTools ++ [
    librelane
    …
  ];
```

Then to create a devshell with both LibreLane and the plugin available, use this
Nix expression:

```nix
devShells = librelane.inputs.nix-eda.forAllSystems { withInputs = [librelane self]; } (utils: with utils; {
  default = callPackage (librelane.createOpenLaneShell {
    extra-python-packages = [
      pkgs.librelane_plugin_example
    ];
  }) {};
});
```

For a full example of this, see
[`librelane_plugin_example`](https://github.com/efabless/user_plugin_example).
