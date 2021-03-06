# Release Notes

All notable changes to this project will be documented in this file. This project adheres to [Semantic Versioning](https://semver.org/).

## 1.3.0

Daeploy goes Open Source and free to use for any purpose! 

### New Features

- It is no longer necessary to activate Daeploy with a license to get indefinite access

## 1.2.0

### New Features

- New admin only API functionality to manage users. Users no longer tied to the license
- CLI commands for user management
- Improved logging for s2i errors

## 1.1.1

### New Features

- Daeploy now uses a custom s2i builder image which makes daeploy images much smaller.

### Bugfixes

- Fixed bug where sometimes the image tag would not be saved in the image tar file when deploying local images

## 1.1.0

### New Features

- Added the option to deploy from a local docker image with the CLI.
- Added the option to keep the docker image when killing services
- Added links to service paths to the dashboard
- Improved redirecting of urls after logging in
- Added `disable_http_logs` argument to `service.add_parameter`

### Bugfixes

- Solved critical authentication bug when restarting manager with new settings

## 1.0.2

- Changed database cleaning to be made periodically to keep database writes fast
- Added `DAEPLOY_SERVICE_DB_CLEAN_INTERVAL` service environment variable to control clean interval
- Added manager notification if `service.call_every` call takes longer than period
- Cleaned up the `daeploy init` service

### UI changes

- Updated dashboard with new logo
- Updated documentation with new logo

## 1.0.1

### Bugfixes

- Fixed a bug with mail notifications when timer is active
- Fixed a bug when service table names contain special characters
- Fixed a bug when streaming logs on firefox

## 1.0.0

Official release. The product is deemed ready for use in a production setting.
