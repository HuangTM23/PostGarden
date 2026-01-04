package com.example.postgarden.data

import android.util.Log
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
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

    companion object {
        private const val TAG = "ApiClient"
        const val BASE_URL = "https://huangtm23.github.io/PostGarden" // Now public and accessible via ApiClient.BASE_URL
    }

    suspend fun getReport(reportType: String): List<PolishedNewsItem> = withContext(Dispatchers.IO) {
        val url = "$BASE_URL/$reportType.json"
        Log.d(TAG, "Requesting URL: $url")

        val request = Request.Builder().url(url).build()

        try {
            val response = client.newCall(request).execute()
            Log.d(TAG, "Response Code: ${response.code}")

            if (!response.isSuccessful) {
                Log.e(TAG, "Request failed with code ${response.code}: ${response.message}")
                throw IOException("Failed to download file: $response")
            }
            
            val body = response.body?.string()
            Log.d(TAG, "Response Body Size: ${body?.length ?: 0}")

            if (body != null) {
                val type = object : TypeToken<Map<String, List<PolishedNewsItem>>>() {}.type
                val resultMap: Map<String, List<PolishedNewsItem>> = gson.fromJson(body, type)
                val newsList = resultMap["news"] ?: emptyList()
                Log.d(TAG, "Successfully parsed ${newsList.size} news items.")
                return@withContext newsList
            }
        } catch (e: Exception) {
            Log.e(TAG, "Exception during API call: ${e.message}", e)
        }
        return@withContext emptyList<PolishedNewsItem>()
    }
}
