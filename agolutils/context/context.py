from pathlib import Path
from typing import Any, Dict, Optional, Union

from agolutils.io import load_json


def load_context(
    context: Union[Dict, str, Path], config: Optional[Dict] = None
) -> Dict[str, Any]:
    if isinstance(context, dict):
        assert "__context_relpath" in context
        return context

    relpath = Path(context).resolve().parent
    context = load_json(context)
    context["__context_relpath"] = relpath
    return context


def load_context_cli(config: Optional[Union[str, Path]]) -> Dict[str, Any]:
    return load_context(config)
