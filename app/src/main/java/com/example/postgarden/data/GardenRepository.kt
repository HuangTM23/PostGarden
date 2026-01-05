package com.example.postgarden.data

import com.google.gson.Gson

class GardenRepository(private val storage: FileStorage) {
    private val gson = Gson()

    fun saveReport(reportId: String, items: List<PolishedNewsItem>) {
        val json = gson.toJson(items)
        storage.write("$reportId.json", json)
    }

    fun loadReport(reportId: String): List<PolishedNewsItem> {
        val json = storage.read("$reportId.json") ?: return emptyList()
        val type = object : com.google.gson.reflect.TypeToken<List<PolishedNewsItem>>() {}.type
        return gson.fromJson(json, type)
    }

    fun getSavedReportIds(): List<String> {
        return storage.list()
            .filter { it.endsWith(".json") }
            .map { it.removeSuffix(".json") }
    }
}
