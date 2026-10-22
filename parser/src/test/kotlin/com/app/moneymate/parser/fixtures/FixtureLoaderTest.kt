package com.app.moneymate.parser.fixtures

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.charset.CharacterCodingException
import java.nio.charset.StandardCharsets
import java.text.Normalizer

class FixtureLoaderTest {
    @Test
    fun manifestOrderAndDoubleLoadPreserveEveryByte() {
        val first = FixtureLoader().loadAll()
        val second = FixtureLoader().loadAll()
        val expectedOrder =
            listOf("bidv", "msb", "mb").flatMap { bank ->
                listOf("txn_in_01", "txn_out_01", "invalid_missing_amount_01", "noise_notice_01", "noise_promotion_01")
                    .map { case -> "${bank}_$case" }
            }
        assertEquals(expectedOrder, first.map { it.id })
        assertEquals(first.map { it.id }, second.map { it.id })
        first.zip(second).forEach { (left, right) ->
            assertArrayEquals(left.inputBytes, right.inputBytes)
            assertArrayEquals(left.expectedBytes, right.expectedBytes)
            assertEquals("SYNTHETIC_CONTRACT", left.corpusClass)
            assertTrue(left.packageName.startsWith("com.example.moneymate.fixture."))
            assertTrue(left.body.contains("SYNTHETIC_"))
            assertFalse(left.toString().contains("MEMO"))
            if (left.id.startsWith("mb_") || left.id == "msb_txn_in_01") {
                assertEquals("synthetic_contract", left.provenanceKind)
            }
        }
    }

    @Test
    fun headerReaderPreservesUnicodeWhitespaceAndRejectsMalformedInput() {
        val loader = FixtureLoader()
        val nfc = "SYNTHETIC_Tiếng Việt 😀"
        val nfd = Normalizer.normalize(nfc, Normalizer.Form.NFD)
        listOf("\n", "\r\n").forEach { newline ->
            listOf(nfc, nfd).forEach { unicode ->
                val body = " $unicode\t${newline}${newline}SYNTHETIC_END $newline"
                val text = "# package: test$newline# title: SYNTHETIC_TITLE$newline---$newline$body"
                val parsed = loader.splitHeader(text.toByteArray(StandardCharsets.UTF_8))
                assertEquals("test", parsed.first)
                assertEquals("SYNTHETIC_TITLE", parsed.second)
                assertArrayEquals(body.toByteArray(StandardCharsets.UTF_8), parsed.third.toByteArray(StandardCharsets.UTF_8))
            }
        }
        assertThrows(IllegalArgumentException::class.java) {
            loader.splitHeader("# package: missing-delimiter".toByteArray(StandardCharsets.UTF_8))
        }
        assertThrows(CharacterCodingException::class.java) {
            loader.splitHeader(byteArrayOf(-1))
        }
    }
}
