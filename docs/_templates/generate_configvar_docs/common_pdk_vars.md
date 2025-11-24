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

${ Variable._render_table_md(pdk_variables, myst_anchor_owner_id='')}

(univ_flow_cvars_scl)=
${"##"} SCL-Level

These are variables that affect a specific standard-cell library.

${ Variable._render_table_md(scl_variables, myst_anchor_owner_id='')}
