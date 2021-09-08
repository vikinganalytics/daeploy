# Release Notes

All notable changes to this project will be documented in this file. This project adheres to [Semantic Versioning](https://semver.org/).

## Dev

### New Features

- Added the option to deploy from a local docker image with the CLI.
- Added the option to keep the docker image when killing services
- Added links to service paths to the dashboard

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
