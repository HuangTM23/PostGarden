package com.example.postgarden.data

import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.IOException

// This data class is now used for the final JSON structure from GitHub Pages
data class PolishedNewsItem(
    val rank: Int,
    val title: String,
    val content: String,
    val source_platform: String = "",
    val source_url: String = "",
    val image: String = ""
)

class ApiClient {
    private val client = OkHttpClient()
    private val gson = Gson()

    // IMPORTANT: Replace with your actual GitHub Pages URL structure
    private val BASE_URL = "https://<YOUR_USERNAME>.github.io/<YOUR_REPO_NAME>"

    suspend fun getReport(reportType: String): List<PolishedNewsItem> {
        if (BASE_URL.contains("<YOUR_USERNAME>")) {
            // Return dummy data if URL is not configured
            return listOf(PolishedNewsItem(
                rank = 0,
                title = "Please configure the URL in ApiClient.kt",
                content = "The BASE_URL in ApiClient.kt needs to be updated with your GitHub Pages URL."
            ))
        }

        val url = "$BASE_URL/$reportType.json" // e.g. .../morning.json
        val request = Request.Builder().url(url).build()

        try {
            val response = client.newCall(request).execute()
            if (!response.isSuccessful) {
                throw IOException("Failed to download file: $response")
            }
            val body = response.body?.string()
            if (body != null) {
                // The JSON from the file is expected to have a "news" key containing the list
                val type = object : TypeToken<Map<String, List<PolishedNewsItem>>>() {}.type
                val resultMap: Map<String, List<PolishedNewsItem>> = gson.fromJson(body, type)
                return resultMap["news"] ?: emptyList()
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
        return emptyList()
    }
}
