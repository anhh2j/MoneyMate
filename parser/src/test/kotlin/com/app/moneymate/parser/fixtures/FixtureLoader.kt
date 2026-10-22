package com.app.moneymate.parser.fixtures

import java.nio.charset.CodingErrorAction
import java.nio.charset.StandardCharsets

/** Reads the restricted manifest metadata after the independent Python contract validator. */
class FixtureLoader {
    class LoadedFixture(
        val id: String,
        val corpusClass: String,
        val provenanceKind: String,
        val inputBytes: ByteArray,
        val expectedBytes: ByteArray,
        private val fields: Triple<String, String, String>,
    ) {
        val packageName: String get() = fields.first
        val title: String get() = fields.second
        val body: String get() = fields.third

        override fun toString(): String = "LoadedFixture(id=$id)"
    }

    fun loadAll(): List<LoadedFixture> {
        val manifest = decode(resource("manifest.json"))
        require(manifest.contains("\"corpusClass\": \"SYNTHETIC_CONTRACT\"")) { "CORPUS_CLASS" }
        val ids = fields(manifest, "id")
        val inputs = fields(manifest, "inputPath")
        val expected = fields(manifest, "expectedPath")
        val kinds = fields(manifest, "kind")
        require(ids.size == CASE_COUNT && ids.distinct().size == ids.size) { "MANIFEST_IDS" }
        require(listOf(inputs, expected, kinds).all { it.size == ids.size }) { "MANIFEST_METADATA" }
        return ids.indices.map { index ->
            load(ids[index], inputs[index], expected[index], kinds[index])
        }
    }

    private fun load(
        id: String,
        input: String,
        expected: String,
        kind: String,
    ): LoadedFixture {
        require(kind in setOf("synthetic_contract", "synthetic_from_observed_structure")) { "PROVENANCE" }
        val raw = resource(input)
        val parts = splitHeader(raw)
        return LoadedFixture(
            id,
            "SYNTHETIC_CONTRACT",
            kind,
            raw,
            resource(expected),
            parts,
        )
    }

    internal fun splitHeader(raw: ByteArray): Triple<String, String, String> {
        val match = HEADER.matchEntire(decode(raw))
        requireNotNull(match) { "HEADER_FORMAT" }
        return Triple(match.groupValues[1], match.groupValues[2], match.groupValues[3])
    }

    private fun fields(
        json: String,
        name: String,
    ): List<String> {
        val pattern = Regex("\"$name\"\\s*:\\s*\"([A-Za-z0-9_./:-]+)\"")
        return pattern.findAll(json).map { it.groupValues[1] }.toList()
    }

    private fun resource(path: String): ByteArray {
        require(SAFE_PATH.matches(path) && !path.contains("..") && !path.startsWith("/")) { "RESOURCE_PATH" }
        val stream = javaClass.getResourceAsStream("/$path")
        requireNotNull(stream) { "RESOURCE_MISSING" }
        return stream.use { it.readBytes() }
    }

    private fun decode(bytes: ByteArray): String =
        StandardCharsets.UTF_8
            .newDecoder()
            .onMalformedInput(CodingErrorAction.REPORT)
            .onUnmappableCharacter(CodingErrorAction.REPORT)
            .decode(java.nio.ByteBuffer.wrap(bytes))
            .toString()

    private companion object {
        const val CASE_COUNT = 15
        val SAFE_PATH = Regex("[A-Za-z0-9_./-]+")
        val HEADER = Regex("# package: ([^\\r\\n]+)\\r?\\n# title: ([^\\r\\n]*)\\r?\\n---\\r?\\n([\\s\\S]*)")
    }
}
