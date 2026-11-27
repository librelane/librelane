from io import TextIOWrapper

class LibertyAst:
    id: str
    value: str
    args: list[str]
    children: list[LibertyAst]

    def find(self, name: str) -> LibertyAst: ...

class LibertyParser:
    ast: LibertyAst
    def __init__(self, file: TextIOWrapper) -> None: ...
