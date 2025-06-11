# The LibreLane Documentation

LibreLane is a powerful and versatile infrastructure library that enables the
construction of digital ASIC implementation flows based on open-source and
commercial EDA tools. It includes a reference flow ({flow}`Classic`) that is
built entirely using open-source EDA tools, and allowing designers to abstract
the underlying tools and configure their behavior with a single configuration
file.

LibreLane also supports the ability to freely extend or modify flows using
Python scripts and utilities.

Currently, LibreLane and its default flow support all variants of the
open-source [Skywater PDK](https://github.com/google/skywater-pdk) and some
variants of the open-source
[GlobalFoundries PDK](https://github.com/google/gf180mcu-pdk).

See [Using PDKs](./usage/about_pdks.md) for more info.

Here are some of the key benefits of using LibreLane:

* **Flexibility and extensibility**: LibreLane is designed to be flexible and
  extensible, allowing designers to customize flows to meet their specific
  needs. This can be done by writing Python scripts and utilities,
  or by modifying the existing configuration file.
* **Open source**: LibreLane is an open-source project, which means that it is
  freely available to use and modify. This makes it a good choice for designers
  who are looking for a cost-effective and transparent solution.
* **Community support**: LibreLane capitalizes on LibreLane's existing community of
  users and contributors. This means that there is a wealth of resources
  available to help designers get started and troubleshoot any problems
  they encounter.

Follow the navigation element below (or check the sidebar on the left) to
get started.

```{toctree}
:glob:
:hidden:

getting_started/index
usage/index
reference/index
additional_material
glossary
faq
contributors/index
```
