# Built-in Steps and their Configuration Variables
These steps are included with LibreLane and are used by its various built-in
flows.

This page documents these steps, how to get them and their configuration
variables (if applicable).

If you're looking for documentation for the `Step` Python classes themselves,
check the API reference [here](./api/steps/index).

```{admonition} Warnings
:class: warning

* Two steps in a given Flow may share a configuration variable name
  if-and-only-if the variables are otherwise identical, i.e., the name, type,
  and default value all match. Otherwise, the flow will not compile.
* Some steps have a variable prefixed with `RUN_` that enables or disables said
  step. This is a vestige from LibreLane 1 and it is recommended to explicitly
  specify your flow either by using the API or in your JSON configuration file's
  `meta` object.
```

```{admonition} Notes
:class: note

* `?` indicates an optional variable, i.e., a value that may hold a value of
  `None`.  LibreLane steps are expected to understand that these values are
  optional and behave accordingly.

* Variable names denoted (<sup>PDK</sup>) are expected to be declared by the PDK.

  If a PDK does not define one of the required variables, it is considered to be
  incompatible with this step.
```

```{tip}
For a table of contents, press the following button on the top-right corner
of the page: <svg stroke="currentColor" fill="currentColor" stroke-width="0" viewBox="0 0 1024 1024" height="16px" style="vertical-align: middle;">
    <path d="M408 442h480c4.4 0 8-3.6 8-8v-56c0-4.4-3.6-8-8-8H408c-4.4 0-8 3.6-8 8v56c0 4.4 3.6 8 8 8zm-8 204c0 4.4 3.6 8 8 8h480c4.4 0 8-3.6 8-8v-56c0-4.4-3.6-8-8-8H408c-4.4 0-8 3.6-8 8v56zm504-486H120c-4.4 0-8 3.6-8 8v56c0 4.4 3.6 8 8 8h784c4.4 0 8-3.6 8-8v-56c0-4.4-3.6-8-8-8zm0 632H120c-4.4 0-8 3.6-8 8v56c0 4.4 3.6 8 8 8h784c4.4 0 8-3.6 8-8v-56c0-4.4-3.6-8-8-8zM115.4 518.9L271.7 642c5.8 4.6 14.4.5 14.4-6.9V388.9c0-7.4-8.5-11.5-14.4-6.9L115.4 505.1a8.74 8.74 0 0 0 0 13.8z"></path>
</svg>
```

%for category, steps in categories_sorted:
${"##"} ${category}
%for key, step in steps:
${step.get_help_md(use_dropdown=True)}
<hr />

%endfor
<hr />

%endfor
