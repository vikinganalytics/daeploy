from pathlib import Path

from IPython.core.magic import register_cell_magic


@register_cell_magic
def service_cell(project_dir, cell):
    """Create the necessary boilerplate for a daeploy service and write the
    cell contents to the service.py file.

    Args:
        project_dir (str): Path to the project directory
        cell (str): Jupyter notebook cell to save to service.py

    Returns:
        str: "Saved requirements.txt" on success
    """
    msg = ""

    project_dir = Path(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)

    # Create environment file
    environment_path = project_dir / ".s2i" / "environment"
    environment_path.parent.mkdir(exist_ok=True)
    if not environment_path.is_file():
        with open(environment_path, "w") as file_handle:
            file_handle.write("APP_FILE = service.py")
        msg += f"Created project {project_dir}. "

    # Create requirements.txt file with daeploy
    requirements_path = project_dir / "requirements.txt"
    if not requirements_path.is_file():
        with open(requirements_path, "w") as file_handle:
            file_handle.write("daeploy")

    # Save the cell contents to service.py
    with open(project_dir / "service.py", "w") as file_handle:
        file_handle.write(cell)
    msg += "Saved service.py"

    return msg


@register_cell_magic
def service_requirements(project_dir, cell):
    """Add packages to the service requirements.txt file

    Args:
        project_dir (str): Path to the project directory
        cell (str): Jupyter notebook cell to save to service.py

    Raises:
        FileNotFoundError: If the project does not exist

    Returns:
        str: "Saved requirements.txt" on success
    """
    project_dir = Path(project_dir)
    if not project_dir.is_dir():
        raise FileNotFoundError(
            f"The project {project_dir} does not exist. "
            f"Please run %%service_cell {project_dir} first."
        )

    if "daeploy" not in cell:
        cell = "daeploy\n" + cell

    with open(project_dir / "requirements.txt", "w") as file_handle:
        file_handle.write(cell)

    return "Saved requirements.txt"
