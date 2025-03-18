import sys
from pathlib import Path
from typing import List, Tuple


def resolve_paths(input_path, output_path) -> Tuple[List[Path], List[Path]]:
    _inp = input_path
    _out = output_path

    # prep input
    if isinstance(input_path, (str, Path)):
        input_path = Path(input_path)
        if input_path.is_dir():
            input_path = sorted(input_path.glob("[!~]*.doc*"))
        else:
            input_path = [input_path]
    if isinstance(input_path, list):
        input_path = [
            Path(p).resolve() for p in input_path if Path(p).suffix in [".docx", ".doc"]
        ]
        assert len(input_path) > 0, (_inp, input_path)
    else:
        raise ValueError(f"unexpected input for `input_path`:{_inp}")

    # prep output
    if output_path is None:
        output_path = [
            input_path[0].parent / (str(inp.stem) + ".pdf") for inp in input_path
        ]

    if isinstance(output_path, (str, Path)):
        output_path = Path(output_path)
        if output_path.is_dir():
            output_path = [output_path / (str(inp.stem) + ".pdf") for inp in input_path]

    if isinstance(output_path, list):
        output_path = [
            Path(p).resolve() for p in output_path if Path(p).suffix in [".pdf"]
        ]
        assert len(output_path) == len(input_path), (_out, output_path)
    else:
        raise ValueError(f"unexpected input for `output_path`:{_out}")

    return input_path, output_path


def convert(input_path, output_path=None, word=None):
    inps, outs = resolve_paths(input_path, output_path)
    if sys.platform == "win32":
        from .msword import save_as_pdf

        return save_as_pdf(inps, outs, word=word)
    else:
        raise NotImplementedError("Not implemented for linux or darwin systems.")
