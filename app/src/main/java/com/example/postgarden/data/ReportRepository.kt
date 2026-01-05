package com.example.postgarden.data

import android.content.Context
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class ReportRepository(private val context: Context) {

    private val gson = Gson()
    private val historyDir = File(context.filesDir, "history")

    init {
        if (!historyDir.exists()) {
            historyDir.mkdirs()
        }
    }

    fun saveReport(type: String, jsonContent: String) {
        val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date())
        // filename: history_20260105_100000_morning.json
        val filename = "history_${timestamp}_${type}.json"
        val file = File(historyDir, filename)
        file.writeText(jsonContent)
    }

    fun getHistoryFiles(): List<File> {
        return historyDir.listFiles()?.toList()?.sortedByDescending { it.lastModified() } ?: emptyList()
    }

    fun loadReport(file: File): List<PolishedNewsItem> {
        val json = file.readText()
        val type = object : TypeToken<Map<String, List<PolishedNewsItem>>>() {}.type
        val resultMap: Map<String, List<PolishedNewsItem>> = gson.fromJson(json, type)
        return resultMap["news"] ?: emptyList()
    }
    
    fun getLatestReport(): List<PolishedNewsItem>? {
        val files = getHistoryFiles()
        if (files.isNotEmpty()) {
            return loadReport(files.first())
        }
        return null
    }
}
