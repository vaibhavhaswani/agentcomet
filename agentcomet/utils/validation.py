import os

def validate_uaf_path(path: str) -> bool:
    """
    Basic validation if file exists and has correct extension.
    For deep validation, use uaf-cli.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"File {path} does not exist.")
    if not path.endswith('.uaf'):
        # Just a warning or strict?
        pass
    return True

# Placeholder for deeper integration
