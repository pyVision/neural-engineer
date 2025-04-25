# Modern Python Project Management with Poetry

## Introduction

Managing dependencies and creating reproducible environments in Python projects has historically been a challenging task. Python's ecosystem offers several tools for package management, but they often come with limitations in terms of dependency resolution, environment isolation, and project packaging.

Poetry is a modern Python package and dependency manager that aims to solve these problems. It provides a comprehensive solution for managing Python projects from dependency management to building and publishing packages. In this blog, we'll explore Poetry's capabilities, how it improves upon traditional tools like pip, and how it can streamline your Python development workflow.

## Why Poetry is Better Than pip

While pip has served as Python's default package installer for years, it has several limitations that Poetry addresses:

### 1. Dependency Resolution

**pip**: Lacks sophisticated dependency resolution, which can lead to conflicts. It installs what you ask for without ensuring all dependencies are compatible with each other.

**Poetry**: Offers deterministic dependency resolution, ensuring all packages in your project work together without conflicts. Poetry uses a SAT solver to find a set of package versions that satisfy all dependencies.

### 2. Environment Management

**pip**: Requires separate tools like venv or virtualenv for environment management.

**Poetry**: Integrates virtual environment creation and management directly, simplifying the workflow.

### 3. Lock Files

**pip**: Requirements files are static and don't automatically track sub-dependencies. You can use `pip freeze > requirements.txt` but this doesn't distinguish between direct and transitive dependencies.

**Poetry**: Automatically creates and updates a `poetry.lock` file that locks all dependencies and their dependencies, ensuring reproducible builds across different environments.

### 4. Project Metadata

**pip**: Requires separate configuration for package metadata in `setup.py` or `setup.cfg`.

**Poetry**: Manages all project configuration in a single `pyproject.toml` file, following PEP 518 standards.

### 5. Publishing Workflow

**pip**: Doesn't handle package building and publishing. You need additional tools like twine.

**Poetry**: Provides a complete workflow for building and publishing packages to PyPI.

## Installation and Uninstallation

### Installing Poetry

Poetry can be installed using the recommended installer script:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

After installation, you might need to add Poetry to your PATH. The installer will provide instructions for your specific operating system.

### Verifying Installation

```bash
poetry --version
```

### Uninstalling Poetry

```bash
curl -sSL https://install.python-poetry.org | python3 - --uninstall
```


## Creating and Managing Projects

### Creating a New Project

To create a new Poetry project:

```bash
poetry new my-project
```

This will create a new directory with the following structure:

```
my-project/
├── pyproject.toml
├── README.md
├── my_project/
│   └── __init__.py
└── tests/
    └── __init__.py
```

Alternatively, if you want to set up Poetry in an existing project:

```bash
cd existing-project
poetry init
```

This will guide you through a series of prompts to create a `pyproject.toml` file.

### Adding Dependencies

```bash
# Add a dependency
poetry add requests

# Add a development dependency
poetry add pytest --dev

# Add a dependency with version constraints
poetry add "django>=4.0.0,<5.0.0"
```

### Removing Dependencies

```bash
poetry remove requests
```

### Updating Dependencies

```bash
# Update all dependencies
poetry update

# Update specific dependencies
poetry update requests pytest
```

## Project Directory Structure

A typical Poetry project has the following structure:

```
project-name/
├── pyproject.toml         # Project configuration and dependencies
├── poetry.lock            # Lock file with exact versions of all dependencies
├── README.md              # Project documentation
├── project_name/          # Source code directory
│   ├── __init__.py        # Makes the directory a package
│   └── main.py            # Main module
├── tests/                 # Test directory
│   ├── __init__.py
│   └── test_main.py       # Test modules
└── .gitignore             # Git ignore file
```

The `pyproject.toml` file is the heart of a Poetry project. It contains:

- Project metadata (name, version, description, authors)
- Dependencies
- Development dependencies
- Build system requirements
- Optional: scripts, plugins, and other project configuration

## Packaging and Building


### Building Packages

To build your package:

```bash
poetry build
```

This creates two formats in the `dist/` directory:
- Source distribution (`.tar.gz`)
- Wheel distribution (`.whl`)

### Including Data and Configuration Files

To include non-Python files (like data, configuration files, or assets) in your package:

1. Add them to the `package-data` field in `pyproject.toml`:

```toml
[tool.poetry]
# ...other configuration...
include = [
    "data/*.json",
    "config/*.yaml",
    "static/**/*"
]
```

2. For more complex needs, create a `MANIFEST.in` file in your project root:

```
include data/*.json
include config/*.yaml
recursive-include static *
```

Access these files in your code using the `importlib.resources` module (Python 3.7+):

```python
from importlib import resources

# For text files
config_text = resources.read_text("your_package.config", "settings.yaml")

# For binary files
image_data = resources.read_binary("your_package.static", "logo.png")

# Get file path directly
with resources.path("your_package.data", "large_dataset.bin") as file_path:
    # Now file_path is a pathlib.Path object you can use
    print(f"File path: {file_path}")
    with open(file_path, "rb") as f:
        binary_data = f.read()
```

Or for earlier Python versions:

```python
import os
import pkg_resources

config_path = pkg_resources.resource_filename("your_package", "config/settings.yaml")
```

### Installing from dist files

You can initialize a Poetry project non-interactively by using the `--no-interaction` flag with the `init` command:

```bash
poetry init --no-interaction --name=my-project --dependency=requests
```

You can specify various parameters:

```bash
poetry init --no-interaction \
    --name=my-project \
    --description="My awesome project" \
    --author="Your Name <your.email@example.com>" \
    --dev-dependency=pytest \
    --python=">=3.11,<4.0"
```

Install the distribution file as a dependency

```bash
poetry add project-0.1.0.tar.gz or
poetry add project-py3-none-any.whl

```

This will install the distribution package and all the dependencies required by the dependency package unlike pip 

Another option is manually copy the distribution file to a location

```bash
tar -xvf project-0.1.0.tar.gz
cd domain_check-0.1.0
poetry install
```

## Running the Project

### Running Scripts

Poetry provides a `run` command that executes commands within the project's virtual environment:

```bash
# Run a Python file
poetry run python your_script.py

# Run a module
poetry run python -m your_module

```

### Defining Custom Scripts

You can define custom scripts in the `pyproject.toml` file:

```toml
[tool.poetry.scripts]
start = "my_package:main"
```

Then run them with:

```bash
poetry run start
```

## Working with Virtual Environments

### Virtual Environment Management

Poetry automatically creates and manages virtual environments for your projects:

```bash
# Activate the virtual environment (creates one if it doesn't exist)
poetry shell

# Exit the virtual environment
exit
```

### Viewing Environment Information

```bash
# Show the path to the virtual environment
poetry env info

# List all virtual environments associated with the project
poetry env list
```

### Custom Virtual Environment Locations

By default, Poetry creates virtual environments in a centralized cache directory. To change this behavior and create the virtual environment within your project directory:

```bash
poetry config virtualenvs.in-project true
```

## Conclusion

Poetry has revolutionized Python project management by providing an all-in-one solution for dependency management, packaging, and publishing. Its intuitive interface, powerful dependency resolution, and adherence to modern Python packaging standards make it an excellent choice for both small scripts and large applications.

By adopting Poetry, you can streamline your development workflow, ensure reproducibility across environments, and focus more on writing code rather than managing dependencies and configuration. As the Python ecosystem continues to evolve, tools like Poetry are leading the way in modernizing project management practices.

## Alternatives to Poetry

While Poetry offers a comprehensive solution, there are other modern tools worth considering:


[uv](https://github.com/astral-sh/uv) is a new, extremely fast Python package installer and resolver written in Rust. It aims to be a drop-in replacement for pip, with these key features:

PDM is another modern Python package manager with PEP 582 support, which means you don't need to create virtual environments explicitly. Key features include:

Pipenv combines pip and virtualenv into a single tool, offering:

While these alternatives each have their strengths, Poetry remains one of the most comprehensive and user-friendly solutions, especially for projects that need packaging and publishing capabilities alongside dependency management.