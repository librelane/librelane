# API Stability Policy

LibreLane strictly follows [semantic versioning](https://semver.org). Any
breaks to the documented API, no matter how trivial, necessitates a major
version increment.

We try not to break the API for any reason, but in the event we decide that an
API-breaking feature is too important, we try to queue up a couple and not
simply have multiple major versions.

The `Changelog.md` at the top of the repository is intended to exhaustively
list all API breaks within a major version increment of LibreLane: anything
missing is a bug.

The API for LibreLane includes all functions, classes, methods and properties in
{doc}`/reference/api`, with these exceptions:

## Private

Any functions, classes, methods and properties prefixed with `__` are considered
private and not part of the API, even if they are documented.

Private class members are unique in that Python itself puts in a half-hearted
effort to prevent external users from using them. So, you know, please don't.

## Internal

Any functions, classes, methods, properties **and function parameters** prefixed
with `_` are considered internal, even if they are documented.

Internal objects are intended for use within the LibreLane codebase itself and
may be changed as part of even minor versions. You may choose to use them, but
we cannot promise they will continue to work when you update LibreLane, i.e.,
they are not part of the official API.

Do note that for access control purposes, we make a distinction between
`internal` and `protected` similar to the C# programming language: class
members marked protected **ARE** a full part of the API.

See {doc}`/contributors/classes` for more info.

## Undocumented

All undocumented objects are also considered internal regardless of whether
they're prefixed by an underscore or not. We define undocumented objects as
follows:

* Undocumented classes are defined as classes without a top-level string **AND**
  no documented methods.
* Undocumented functions and methods are defined as ``defs``s (including those
  with the `@property` decorator to make them "dynamic properties") without a
  docstring.
* Undocumented properties are defined as properties within undocumented classes
  or those without a non-empty `:param:`, `:ivar`, or `:cvar:` declaration
  within the class docstring.
  * In the documentation, they are listed as **PARAMETERS** and **VARIABLES**
  within a class.

```{note}
If you find something that you really think should be part of the API but was
left undocumented by mistake, please file an issue! We'd really appreciate it!
```
