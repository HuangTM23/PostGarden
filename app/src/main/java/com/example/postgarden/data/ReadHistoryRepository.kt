package com.example.postgarden.data

import android.content.Context
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import java.io.File
import java.util.Date

data class ReadHistoryItem(
    val title: String,
    val url: String,
    val timestamp: Long = System.currentTimeMillis()
)

class ReadHistoryRepository(context: Context) {
    private val file = File(context.filesDir, "read_history.json")
    private val gson = Gson()

    fun getHistory(): List<ReadHistoryItem> {
        if (!file.exists()) return emptyList()
        return try {
            val json = file.readText()
            val type = object : TypeToken<List<ReadHistoryItem>>() {}.type
            gson.fromJson(json, type) ?: emptyList()
        } catch (e: Exception) {
            emptyList()
        }
    }

    fun addHistory(title: String, url: String) {
        val current = getHistory().toMutableList()
        
        // Remove existing entry with same URL to update timestamp and move to top
        current.removeAll { it.url == url }
        
        // Add new item at the beginning
        current.add(0, ReadHistoryItem(title, url))
        
        // Limit history size (e.g., 100 items)
        if (current.size > 100) {
            save(current.subList(0, 100))
        } else {
            save(current)
        }
    }

    fun clearHistory() {
        if (file.exists()) {
            file.delete()
        }
    }

    private fun save(items: List<ReadHistoryItem>) {
        val json = gson.toJson(items)
        file.writeText(json)
    }
}
