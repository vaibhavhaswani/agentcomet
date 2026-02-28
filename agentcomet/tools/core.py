import inspect
from typing import Any, Callable, Dict, get_type_hints

class ToolSpec:
    """Wrapper around a tool function containing its schema for LLM calling."""
    def __init__(self, name: str, fn: Callable, schema: Dict[str, Any], description: str):
        self.name = name
        self.fn = fn
        self.schema = schema
        self.description = description

    def __call__(self, *args, **kwargs):
        return self.fn(*args, **kwargs)

    def __repr__(self):
        return f"<ToolSpec name='{self.name}' description='{self.description[:30]}...'>"

def _python_type_to_json_type(py_type: Any) -> str:
    """Maps Python type hints to JSON Schema types."""
    
    # We unwrap Optionals in type hints natively below,
    # Here we just check base types
    if py_type == int:
        return "integer"
    if py_type == float:
        return "number"
    if py_type == bool:
        return "boolean"
    if py_type == list or py_type == tuple: # simplified
        return "array"
    if py_type == dict:
        return "object"
    return "string"

def tool(fn: Callable) -> ToolSpec:
    """
    Decorator that converts a standard Python function into a ToolSpec.
    It extracts the name, a JSON schema based on its parameters and type annotations,
    and a description from the docstring.
    """
    name = fn.__name__
    description = inspect.getdoc(fn) or ""
    
    # Infer schema from signature and type hints
    sig = inspect.signature(fn)
    try:
        hints = get_type_hints(fn)
    except Exception:
        hints = {}

    properties = {}
    required = []

    for param_name, param in sig.parameters.items():
        if param_name == "self" or param_name == "cls":
            continue
            
        param_type = hints.get(param_name, str)
        
        # Determine if required
        is_required = param.default == inspect.Parameter.empty
        if is_required:
            required.append(param_name)

        properties[param_name] = {
            "type": _python_type_to_json_type(param_type),
            "description": f"Parameter {param_name}" # Optional: Parse Sphinx/Google docstrings for per-param descriptions
        }

    schema = {
        "type": "object",
        "properties": properties,
        "required": required
    }

    return ToolSpec(
        name=name,
        fn=fn,
        schema=schema,
        description=description
    )
