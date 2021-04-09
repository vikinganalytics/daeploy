# Daeploy project skeleton template

The template should be updated to contain necessary boilerplate code for creating a daeploy service using the SDK. A project is created from the template through the CLI by using the function `daeploy init`.

## Usage guide

The template was made using [cookiecutter](https://cookiecutter.readthedocs.io/en/1.7.2/). Cookiecutter works by using the `{{}}` notation within which you can write python code. Project specific variables, such as project name, author, etc. is set in the `cookiecutter.json` file in the template root. These variables can then be reached in every file, e.g `{{cookiecutter.project_name}}` will be replaced by the project name chosen by the user. This works both inside of files as well as for file/directory names.
