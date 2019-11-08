# NMOS Query API Implementation Changelog

## 0.7.10
- Alter executable to run using Python3, alter `stdeb` to replace python 2 package

## 0.7.9
- Clean-up before stopping service thread

## 0.7.8
- Add api downgrade function from nmoscommon

## 0.7.7
- Add `api_auth` text record to multicast announcements

## 0.7.6
- Import config from separate file, add OAUTH_MODE config parameter

## 0.7.5
- Add cleanup function when stopping service

## 0.7.4
- Move NMOS packages from recommends to depends

## 0.7.3
- Add systemd ready notification when service has started

## 0.7.2
- Add Python3 linting stage to CI and remove deprecated `cmp` keyword

## 0.7.1
- Fix missing files in Python 3 Debian package

## 0.7.0
- Added NMOS Security Decorators for OAuth2 Authorization and fixed linting

## 0.6.0
- Use nmoscommon prefer_hostnames/node_hostname to inform all absolute hrefs

## 0.5.7
- Added python3 to testing and packaging

## 0.5.6
- Fix bug causing some missing messages via WebSockets
- Fix bugs responding when multiple similar WebSockets are open

## 0.5.5
- Fix bug preventing use of priorities between 1 and 99

## 0.5.4
- Fix bug in websocket message format

## 0.5.3
- Ensure only wss:// connections can be created in secure mode

## 0.5.2
- Fix compatibility with older versions of Requests which define exceptions differently

## 0.5.1
- Fix bug that causes "Read timed out." messages to be logged when communicating with etcd in normal circumstances

## 0.5.0
- Add config option to enable/disable mDNS announcement

## 0.4.0
- Disable v1.0 API when running in HTTPS mode

## 0.3.0
- Add provisional support for IS-04 v1.3
