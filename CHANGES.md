# Release Notes

All notable changes to this project will be documented in this file. This project adheres to [Semantic Versioning](https://semver.org/).

## Dev

- Changed database cleaning to be made periodically to keep database writes fast
- Added `DAEPLOY_SERVICE_DB_CLEAN_INTERVAL` service environment variable to control clean interval
- Added manager notification if `service.call_every` call takes longer than period

## 1.0.1

### Bugfixes:

- Fixed a bug with mail notifications when timer is active
- Fixed a bug when service table names contain special characters
- Fixed a bug when streaming logs on firefox

## 1.0.0

Official release. The product is deemed ready for use in a production setting.
