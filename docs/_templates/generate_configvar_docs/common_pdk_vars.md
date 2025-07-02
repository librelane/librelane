# Universal Flow PDK Configuration Variables

These are variables that are to be defined by a process design kit's
configuration files for *all* steps and flows. For a PDK to be compatible with
LibreLane, all non-`Optional` variables *must* be given a value.

Like with flow configuration variables, configuration objects can freely
override these values.

```{note}
`?` indicates an optional variable, i.e., a value that does not need to be
implemented by a PDK or an SCL. LibreLane steps are expected to understand that
these values may hold a value of `None` in the input configuration and
behave accordingly.
```

(univ_flow_cvars_pdk)=
${"##"} PDK-Level

These are variables that affect the entire PDK.


| Variable Name | Type | Description | Units |
| - | - | - | - |
%for var in pdk_variables:
| `${var.name}`{#${var._get_docs_identifier()}} | ${var.type_repr_md(for_document=True)} | ${var.desc_repr_md()} | ${var.units or ""} |
%endfor

(univ_flow_cvars_scl)=
${"##"} SCL-Level

These are variables that affect a specific standard-cell library.

| Variable Name | Type | Description | Units |
| - | - | - | - |
%for var in scl_variables:
| `${var.name}`{#${var._get_docs_identifier()}} | ${var.type_repr_md(for_document=True)}  | ${var.desc_repr_md()} | ${var.units or ""} |
%endfor
