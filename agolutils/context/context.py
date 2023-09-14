from pathlib import Path
import json
from typing import Any, Dict, Optional, Union

from agolutils.io import load_json


def load_context(context: Union[Dict, str, Path]) -> Dict[str, Any]:
    if isinstance(context, dict):
        assert "__context_relpath" in context
        return context

    relpath = Path(context).resolve().parent
    context = load_json(context)
    context["__context_relpath"] = relpath
    return context


def write_context(mapping: dict, outpath=None):
    if outpath is None:
        outpath = "./context.json"
    out_file = Path(outpath)

    ctx = json.dumps(mapping, indent=2, default=str)
    out_file.write_text(ctx)

    return out_file


def load_context_cli(context: Optional[Union[str, Path]]) -> Dict[str, Any]:
    return load_context(context)
