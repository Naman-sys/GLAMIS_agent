from pathlib import Path
from string import Template

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt(prompt_name: str, subdirectory: str = "") -> str:
    """
    Load a prompt template from the prompts directory.
    
    Args:
        prompt_name: Name of the prompt file (without .txt extension)
        subdirectory: Optional subdirectory within prompts/ (e.g., "subjects")
    
    Returns:
        Prompt template content
    """
    if prompt_name.endswith(".txt"):
        prompt_name = prompt_name[: -len(".txt")]

    if subdirectory:
        prompt_path = PROMPT_DIR / subdirectory / f"{prompt_name}.txt"
    else:
        prompt_path = PROMPT_DIR / f"{prompt_name}.txt"
    
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    
    return prompt_path.read_text(encoding="utf-8")


def render_prompt(prompt_name: str, variables: dict[str, object], subdirectory: str = "") -> str:
    """
    Render a prompt using string.Template syntax.
    
    Args:
        prompt_name: Name of the prompt file (without .txt extension)
        variables: Dictionary of variables to substitute
        subdirectory: Optional subdirectory within prompts/
    
    Returns:
        Rendered prompt with variables substituted
    """
    template = Template(load_prompt(prompt_name, subdirectory))
    return template.safe_substitute({key: str(value) for key, value in variables.items()})


def load_subject_prompt(subject: str) -> str:
    """
    Load a subject-specific prompt.
    
    Args:
        subject: Subject name (e.g., "dsa", "os", "cn", "dbms", "ml", "cybersecurity")
    
    Returns:
        Subject prompt template content
    """
    return load_prompt(f"subject_{subject}", subdirectory="subjects")


def render_subject_prompt(subject: str, variables: dict[str, object]) -> str:
    """
    Render a subject-specific prompt.
    
    Args:
        subject: Subject name
        variables: Dictionary of variables to substitute
    
    Returns:
        Rendered subject prompt
    """
    return render_prompt(f"subject_{subject}", variables, subdirectory="subjects")
