package com.example.postgarden.data

import android.util.Log
import com.google.gson.Gson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request

data class LatestVersions(
    val home: String? = null,
    val world: String? = null,
    val entertainment: String? = null
)

class ApiClient {
    private val client = OkHttpClient()
    private val gson = Gson()

    companion object {
        private const val TAG = "ApiClient"
        const val BASE_URL = "https://huangtm23.github.io/PostGarden"
    }

    suspend fun fetchLatestVersions(): LatestVersions? = withContext(Dispatchers.IO) {
        val url = "$BASE_URL/latest_versions.json"
        Log.d(TAG, "Requesting versions: $url")
        val request = Request.Builder().url(url).build()

        try {
            val response = client.newCall(request).execute()
            if (!response.isSuccessful) {
                Log.e(TAG, "Fetch failed. Code: ${response.code}, Msg: ${response.message}")
                return@withContext null
            }
            val json = response.body?.string()
            if (json == null) {
                Log.e(TAG, "Response body is null")
                return@withContext null
            }
            return@withContext gson.fromJson(json, LatestVersions::class.java)
        } catch (e: Exception) {
            Log.e(TAG, "Exception fetching versions: ${e.message}", e)
            return@withContext null
        }
    }
}
