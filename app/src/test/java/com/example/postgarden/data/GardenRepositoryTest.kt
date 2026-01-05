package com.example.postgarden.data

import org.junit.Assert.assertEquals
import org.junit.Test

class GardenRepositoryTest {

    class FakeFileStorage : FileStorage {
        val files = mutableMapOf<String, String>()

        override fun write(filename: String, content: String) {
            files[filename] = content
        }

        override fun read(filename: String): String? {
            return files[filename]
        }

        override fun list(): List<String> {
            return files.keys.toList()
        }
    }

    @Test
    fun testSaveAndLoadReport() {
        val storage = FakeFileStorage()
        val repository = GardenRepository(storage)

        val items = listOf(
            PolishedNewsItem(1, "Title 1", "Content 1"),
            PolishedNewsItem(2, "Title 2", "Content 2")
        )

        repository.saveReport("morning_20260105", items)

        val loadedItems = repository.loadReport("morning_20260105")
        assertEquals(2, loadedItems.size)
        assertEquals("Title 1", loadedItems[0].title)
        assertEquals("Title 2", loadedItems[1].title)
    }

    @Test
    fun testListSavedReports() {
        val storage = FakeFileStorage()
        val repository = GardenRepository(storage)

        repository.saveReport("report1", emptyList())
        repository.saveReport("report2", emptyList())

        val ids = repository.getSavedReportIds()
        assertEquals(2, ids.size)
        assert(ids.contains("report1"))
        assert(ids.contains("report2"))
    }
}
