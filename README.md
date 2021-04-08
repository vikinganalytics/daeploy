# Daeploy

## Branching strategy

This repo is maintained using the following branching strategy:
- **master**, holds "releasable code"
- **develop**, default branch

The workflow is thuys as follows:
- Releases are handled as tags off of master. 
- Urgent bug-fixes are branched of master and PR:ed to master
- New features, enhancements and non-urgent bug-fixes are branched off of develop and PR:ed to develop
- Any urgent bug-fixes merged directly to master should also be merged/rebased to develop (i.e. develop should never be behind master)

## Development setup

Prerequisites:
* WSL2 with ubuntu distribution, see [here](https://docs.microsoft.com/en-us/windows/wsl/install-win10)
* Docker installation setup with WSL2, see [here](https://docs.docker.com/docker-for-windows/wsl/)
* Python >= 3.6
* Source to image. Check the installation section in [here](https://github.com/openshift/source-to-image)
* Traefik reverse proxy (latest version is 2.3.1 (2020-10-14))
  ```bash
  mkdir tmp
  wget -c https://github.com/traefik/traefik/releases/download/v2.3.1/traefik_v2.3.1_linux_amd64.tar.gz -P tmp/
  tar -zxvf tmp/traefik_v2.3.1_linux_amd64.tar.gz -C tmp/
  sudo cp tmp/traefik /usr/local/bin/
  rm -r tmp/
  ```
* (Optional but handy since it includes debug setups) VS code

All of the following commands should be executed in a WSL2 (ubuntu) environment. 

In general it is beneficial to keep files in the linux filesystem (NOT the ```/mnt/c/...```) for better speed and, if necessary, access it through ```\\wsl$``` in the Windows filesystem.

Start by cloning the repo in your wsl.

Setup of virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements_manager.txt
pip install -r requirements_sdk.txt
pip install -r requirements_dev.txt
```

To start manager in auto-reloading development mode:
```bash
uvicorn manager.app:app --reload
```

To run tests:
```bash
python -m pytest tests
```

### Debug

To debug in VS code:
* Make sure you have opened vs code so that the repo root is the workspace, for example according to:
```bash
(venv) freol@LAPTOP-P6BMIDRA:~/dev/daeploy$ code .
```
* Put a breakpoint somewhere in the code and start the app.py file in VS code using the F5 button.

Debugging the SDK and/or the communction between manager/proxy/services:
* Deploy a service, preferably one created using the SDK
* Enter the container via bash by: 
```
docker exec -it {docker_id_for_service} bash
```
* While inside the container you can for instance use `curl` or `python` for debuging.

### Docker build

The manager can be be built as a docker container for development purposes. Commands to be executed from root-folder of repo.

```console
docker build -t daeploy_manager:latest .
```

```console
docker run -v /var/run/docker.sock:/var/run/docker.sock -p 80:80 -p 443:443 -e DAEPLOY_AUTH_ENABLED=True -d daeploy_manager:latest
```

## Accessibility

The application will be available according to the following:

- Docker container listens on ports 80 (http) and 433 (https)
- Proxy listens on ports 5080 (http) (and 5443 (https), NOT fully implemented yet)
- Manager is available at ```/``` (or locally on port 8000)
- Any started services are available at ```/services/{service_name}``` (or locally on ports 8001 and upwards)
- Proxy built-in dashboard is available at ```/proxy/dashboard/```

### Access to container registry

TODO: UPDATE THIS SECTION WHEN UPLOADED TO DOCKER HUB

To give outside users access to VAs github container registry as part of [this](https://vikinganalytics.github.io/daeploy-docs/develop/content/getting_started/installation.html#the-manager) step in the documentation , follow these steps:

- Log in to `va-integrator`s github account (in your browser)
- go to settings -> Developer Settings -> Personal Access Tokens
- click on `Generate new token`
- Name it to something that makes sense (have a look at the names of the existing tokens)
- Make sure the access is only: `read:packages`
- Create the token and update this: https://teams.microsoft.com/l/file/303FE3FF-E541-4D0C-AF9A-D15087CABBF0?tenantId=9c1c78de-ac3a-4e9f-ad7f-cce17816470d&fileType=xlsx&objectUrl=https%3A%2F%2Fvikinganalytics.sharepoint.com%2Fsites%2FInfofromCEO%2FShared%20Documents%2FMVI%2FMVI_licences.xlsx&baseUrl=https%3A%2F%2Fvikinganalytics.sharepoint.com%2Fsites%2FInfofromCEO&serviceName=teams&threadId=19:e444faa6257444a28bd4148b87091f6b@thread.skype&groupId=a2b8a12e-04d6-4937-9a62-b188a797a015
- Send example usage to external user as follows:

```bash
docker login --username va-integrator --password {generated_token} ghcr.io
docker pull ghcr.io/vikinganalytics/mvi/mvi_manager:{version}
```

## Docs

To build the docs as html pages:

### Without multiversion support

```bash
cd docs
make clean html
```

### With multiversion support

```bash
cd docs
sphinx-multiversion source/ build/html/
```

The index HTML page can then be found at `docs/build/html/index.html`

## Scope

Can be found here: [Scope Statement](https://vikinganalytics.sharepoint.com/sites/InfofromCEO/_layouts/15/Doc.aspx?OR=teams&action=edit&sourcedoc={16A4E267-B68C-4EEE-BB65-1458056E1C93})

## Architecture Overview

![](Daeploy_Architecture_Overview.png)
