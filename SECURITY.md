# Security policy

The runtime is an archived research environment with incomplete compatibility and no production-support commitment. The engineering freeze does not imply that vulnerabilities are fixed. No supported security-release series or response-time promise is established.

Before this becomes a public hosted repository, the owner must enable a private vulnerability reporting channel and name a responsible contact. Until then, use an existing verified private channel to the institutional steward; no email address or repository URL is invented here. Do not disclose credentials, exploit payloads, private backend endpoints or personal data in public issues. Do not send reports to Wine-Assembly or JoySword maintainers unless the defect is actually in their project.

An actionable report identifies the affected file/version or hash, the boundary crossed, expected and observed behavior, prerequisites and a minimal description that omits secrets. Explain whether the issue concerns browser host routes, local relay/socket isolation, guest memory, resource paths or private backend configuration. The steward determines any renewed engineering authorization before a fix, reproduction or service action.

The future hosting owner should configure secret scanning, push protection and reviewed branches as described in the [release walkthrough](docs/open-source-release.md). These settings have not been enabled by creating this file. Ignore rules do not remove already tracked secrets or clean Git history.
