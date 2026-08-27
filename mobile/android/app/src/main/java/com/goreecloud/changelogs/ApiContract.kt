package com.goreecloud.changelogs

import java.net.URI

data class ChangelogProject(
    val slug: String,
    val name: String,
    val entryCount: Int,
    val latestEntryAt: String?,
)

data class ChangelogEntry(
    val id: Long,
    val projectSlug: String,
    val projectName: String,
    val occurredAt: String,
    val title: String,
    val category: String,
    val summary: String,
    val purpose: String,
    val validation: String,
    val sourceRef: String,
)

data class ChangelogExportEnvelope(
    val schemaVersion: Int,
    val exportedEntries: Int,
    val ledgerTotalEntries: Int,
    val entries: List<ChangelogEntry>,
)

object ChangelogsApiContract {
    const val SUPPORTED_SCHEMA_VERSION = 1

    fun requireHttpsBaseUrl(raw: String): URI {
        val uri = URI(raw)
        require(uri.scheme.equals("https", ignoreCase = true)) {
            "GoreeCloud Changelogs Android requires HTTPS"
        }
        require(!uri.host.isNullOrBlank()) {
            "GoreeCloud Changelogs Android requires a valid API host"
        }
        require(uri.userInfo == null) {
            "Credentials must not be embedded in the API URL"
        }
        require(uri.query == null && uri.fragment == null) {
            "The API base URL must not contain query or fragment data"
        }
        return uri
    }

    fun requireSupportedSchema(schemaVersion: Int) {
        require(schemaVersion == SUPPORTED_SCHEMA_VERSION) {
            "Unsupported GoreeCloud Changelogs API schema version"
        }
    }

    fun bearerAuthorization(readToken: String): String {
        require(readToken.isNotBlank()) { "Read credential is required" }
        require(!readToken.contains('\n') && !readToken.contains('\r')) {
            "Read credential contains invalid control characters"
        }
        return "Bearer $readToken"
    }
}
