package com.example.postgarden.data

import android.util.Log
import com.google.gson.Gson
import com.google.gson.annotations.SerializedName
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.IOException

// This data class is now used for the final JSON structure from GitHub Pages
data class PolishedNewsItem(
    @SerializedName("rank") val rank: Int,
    @SerializedName("title") val title: String,
    @SerializedName("content") val content: String,
    @SerializedName("source_platform") val sourcePlatform: String = "",
    @SerializedName("source_url") val sourceUrl: String = "",
    @SerializedName("image") val imagePath: String = ""
) {
    val fullImageUrl: String
        get() = if (imagePath.isNotEmpty() && !imagePath.startsWith("http")) {
            "${ApiClient.BASE_URL}/$imagePath"
        } else {
            imagePath
        }
}

class ApiClient {
    private val client = OkHttpClient()
    private val gson = Gson()

    companion object {
        private const val TAG = "ApiClient"
        const val BASE_URL = "https://huangtm23.github.io/PostGarden" // Now public and accessible via ApiClient.BASE_URL
    }

    suspend fun getReport(reportType: String): List<PolishedNewsItem> = withContext(Dispatchers.IO) {
        val json = fetchRaw(reportType)
        if (json != null) {
            try {
                val type = object : TypeToken<Map<String, List<PolishedNewsItem>>>() {}.type
                val resultMap: Map<String, List<PolishedNewsItem>> = gson.fromJson(json, type)
                val newsList = resultMap["news"] ?: emptyList()
                Log.d(TAG, "Successfully parsed ${newsList.size} news items.")
                return@withContext newsList
            } catch (e: Exception) {
                Log.e(TAG, "Exception during parsing: ${e.message}", e)
            }
        }
        return@withContext emptyList<PolishedNewsItem>()
    }

    suspend fun fetchRaw(reportType: String): String? = withContext(Dispatchers.IO) {
        val url = "$BASE_URL/$reportType.json"
        Log.d(TAG, "Requesting URL: $url")
        val request = Request.Builder().url(url).build()

        try {
            val response = client.newCall(request).execute()
            if (!response.isSuccessful) return@withContext null
            return@withContext response.body?.string()
        } catch (e: Exception) {
            Log.e(TAG, "Exception during API call: ${e.message}", e)
            return@withContext null
        }
    }
}
