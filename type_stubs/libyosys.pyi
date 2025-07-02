from typing import List, Iterable

class Design:
    def __init__(self) -> None: ...
    def run_pass(self, *command): ...
    def tee(self, *command, o: str): ...
    def read_verilog_files(
        self,
        files: Iterable[str],
        *,
        top: str,
        synth_parameters: Iterable[str],
        includes: Iterable[str],
        defines: Iterable[str],
        use_synlig: bool = False,
        synlig_defer: bool = False,
        yosys_frontend: str = "YOSYS",
    ): ...
    def add_blackbox_models(
        self,
        models: Iterable[str],
        *,
        includes: Iterable[str],
        defines: Iterable[str],
    ): ...

class Pass:
    @staticmethod
    def call__YOSYS_NAMESPACE_RTLIL_Design__std_vector_string_(
        design: Design, cmd: List[str]
    ): ...
