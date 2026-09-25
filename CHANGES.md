# Release Notes

All notable changes to this project will be documented in this file. This project adheres to [Semantic Versioning](https://semver.org/).

## 1.5.1

### Security

- Bumped manager dependencies to resolve High-severity advisories: `cryptography` (46.0.7 → 50.0.0), `pyjwt` (2.12.1 → 2.13.0), and `python-multipart` (0.0.26 → 0.0.27).

### Bugfixes

- The logs viewer no longer goes blank over time. The manager reused a single Docker log client whose connections leaked whenever a live-follow log stream was closed, so eventually every log request would hang and the page rendered empty. Each log request now uses its own client, released when the stream ends.

## 1.5.0

### New Features

- Logs viewer: in-page search with match highlighting and a match count, one-click export of the full log to a file, and a responsive full-screen console (both service and manager logs).
- Dashboard polish: wider Services panel with a slim, self-explanatory Notifications rail; `LOGS`/`DOCS` rendered as clear buttons with keyboard focus rings; content biased to the top with a small capped gap; and denser service rows so more services fit without scrolling.

### Bugfixes

- Logs export and search now return the actual log instead of a validation error (the view no longer requests the invalid `tail=all`).
- Stabilized the flaky `test_read_timerange` SDK test (a concurrent database clean could trim rows mid-test).

## 1.4.0

### New Features

- Redesigned web UI: a modern dark login, dashboard, and a streaming logs view with a Follow / auto-scroll toggle (for both service and manager logs). Fully self-contained — no external CDNs or hot-linked assets.

### Changed

- Modernized the manager and SDK dependency stack and moved to Python 3.12.

### Bugfixes

- Docker Engine 29 compatibility: `daeploy ls`, the dashboard, and service inspection no longer return HTTP 500 on hosts using the newer Docker storage drivers.

### Breaking

- Dropped Python 3.9. Building services requires the Python 3.12 `daeploy/s2i-python` builder image (release 0.1.3).

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
