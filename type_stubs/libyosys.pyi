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
        use_slang: bool = False,
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
    def call(design: Design, cmd: List[str]): ...
