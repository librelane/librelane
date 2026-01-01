new: old: {
  # Clang 16 flags "register" as an error by default
  lemon-graph = old.lemon-graph.overrideAttrs (finalAttrs: previousAttrs: {
    postPatch = "sed -i 's/register //' lemon/random.h";
  });

  # Platform-specific
  ## Undeclared Platform
  clp =
    if old.system == "aarch64-linux"
    then
      (old.clp.overrideAttrs (finalAttrs: previousAttrs: {
        meta = {
          platforms = previousAttrs.meta.platforms ++ [old.system];
        };
      }))
    else (old.clp);

  ## Clang 16 breaks Jshon
  jshon =
    if (old.stdenv.isDarwin)
    then
      old.jshon.override
      {
        stdenv = old.gccStdenv;
      }
    else (old.jshon);
}
