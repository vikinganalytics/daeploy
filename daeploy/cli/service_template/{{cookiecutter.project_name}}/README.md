# Daeploy project: {{cookiecutter.project_name}}

## Creating the service

The ```service.py``` contains an example service and shows how to use the daeploy SDK.

This example shows:

- How to initiate a daeploy service
- How to register changeable parameters
- How to register functions as entrypoints
- How to log from the service
- How to send notifications from the service
- How to start the service

If the service requires external packages, they should be specified in the `requirements.txt` file.

## Deploying the service

The service can be deployed using the daeploy command-line interface:

From a local directory or tarball (.tar.gz):

```daeploy deploy myservice 0.0.1 <path_to_project>```

From a git repository:

```daeploy deploy myservice 0.0.1 --git <git_url>```

## Documentation

Full documentation of the SDK and the CLI can be found here: [https://vikinganalytics.github.io/daeploy-docs/](https://vikinganalytics.github.io/daeploy-docs/)

## Extra

If you want to change name of the service file ```service.py```, or deploy another file as the
daeploy service then you have to change the ```APP_FILE``` key in the ```.s2i/environment``` file.
