# Security

GoreeCloud Changelogs is an internal GoreeCloud application and historical ledger.

Do not commit passwords, private keys, access tokens, session material, recovery codes, or other reusable secrets to this repository or to changelog entries.

The write API is disabled unless `CHANGELOGS_WRITE_TOKEN` is explicitly configured outside source control. Production deployment must use HTTPS through the approved GoreeCloud publication path and must preserve the service's private-by-default access model.

Security-sensitive defects should be handled as GoreeCloud administrative security work under Wardveil Security by GoreeCloud rather than disclosed through public issue content containing exploitable details.
