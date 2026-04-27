import importlib.util
from pathlib import Path
from app.pipes.base import BasePipe

_registry: dict[str, BasePipe] = {}

def register(pipe: BasePipe) -> None:
    _registry[pipe.name] = pipe

def get(name: str) -> BasePipe | None:
    return _registry.get(name)

def all_pipes() -> list[BasePipe]:
    return list(_registry.values())

def load_dynamic_pipes(pipes_dir: str = "pipes") -> None:
    """Hot-load pipes from the ./pipes/ directory."""
    path = Path(pipes_dir)
    if not path.exists():
        return
    for file in path.glob("*.py"):
        if file.stem.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(file.stem, file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for attr in dir(module):
            obj = getattr(module, attr)
            if (
                isinstance(obj, type)
                and issubclass(obj, BasePipe)
                and obj is not BasePipe
            ):
                instance = obj()
                register(instance)
