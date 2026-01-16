package com.example.postgarden.data

import android.content.Context
import android.util.Log
import com.google.gson.Gson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.BufferedInputStream
import java.io.File
import java.io.FileOutputStream
import java.util.zip.ZipInputStream

data class CachedReport(
    val type: String,
    val version: String,
    val timestamp: Long
)

class ReportRepository(private val context: Context) {

    private val gson = Gson()
    private val client = OkHttpClient()
    
    private val rootDir = context.getExternalFilesDir(null) ?: context.filesDir
    private val baseDir = File(rootDir, "PostGarden")
    private val dataDir = File(baseDir, "data")
    private val extractedDir = File(dataDir, "extracted")
    private val localVersionFile = File(dataDir, "latest_versions.json")

    init {
        if (!dataDir.exists()) dataDir.mkdirs()
        if (!extractedDir.exists()) extractedDir.mkdirs()
    }

    fun getLocalVersions(): LatestVersions? {
        if (!localVersionFile.exists()) return null
        return try {
            gson.fromJson(localVersionFile.readText(), LatestVersions::class.java)
        } catch (e: Exception) {
            null
        }
    }

    fun saveLocalVersions(versions: LatestVersions) {
        try {
            localVersionFile.writeText(gson.toJson(versions))
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    suspend fun ensureSummaries(type: String): Boolean = withContext(Dispatchers.IO) {
        val typeDir = File(extractedDir, type)
        if (!typeDir.exists()) return@withContext false
        
        val report = getLocalReport(type)
        val needsUpdate = report.news.any { it.summary.isNullOrEmpty() && !it.originalTitle.isNullOrEmpty() }
        
        if (needsUpdate) {
            val updatedItems = report.news.map { item ->
                async {
                    if (item.summary.isNullOrEmpty() && !item.originalTitle.isNullOrEmpty()) {
                        item.apply { summary = ContentSummaryFetcher.fetchSummary(sourceUrl) }
                    } else item
                }
            }.awaitAll()
            
            val jsonFile = typeDir.walk()
                .filter { it.isFile && it.name.endsWith(".json") && !it.name.equals("version.txt") }
                .sortedByDescending { it.name.startsWith("polished_") }
                .firstOrNull()
            
            if (jsonFile != null) {
                jsonFile.writeText(gson.toJson(report.copy(news = updatedItems)))
                return@withContext true
            }
        }
        return@withContext false
    }

    suspend fun downloadAndPrepare(type: String, zipFilename: String): Boolean = withContext(Dispatchers.IO) {
        val url = "${ApiClient.BASE_URL}/$zipFilename"
        val zipFile = File(dataDir, zipFilename)
        val typeExtractedDir = File(extractedDir, type)
        
        try {
            val request = Request.Builder().url(url).build()
            val response = client.newCall(request).execute()
            if (!response.isSuccessful) return@withContext false
            
            val source = response.body?.byteStream() ?: return@withContext false
            zipFile.outputStream().use { output -> source.copyTo(output) }
            
            if (typeExtractedDir.exists()) typeExtractedDir.deleteRecursively()
            typeExtractedDir.mkdirs()
            
            ZipInputStream(BufferedInputStream(zipFile.inputStream())).use { zis ->
                var entry = zis.nextEntry
                while (entry != null) {
                    val file = File(typeExtractedDir, entry.name)
                    if (entry.isDirectory) {
                        file.mkdirs()
                    } else {
                        file.parentFile?.mkdirs()
                        FileOutputStream(file).use { fos -> zis.copyTo(fos) }
                    }
                    entry = zis.nextEntry
                }
            }
            
            File(typeExtractedDir, "version.txt").writeText(zipFilename)
            
            // --- NEW: Pre-fetch summaries before finishing preparation ---
            val report = getLocalReport(type)
            if (report.news.isNotEmpty()) {
                val updatedItems = report.news.map { item ->
                    async {
                        if (item.summary.isNullOrEmpty() && !item.originalTitle.isNullOrEmpty()) {
                            item.apply { summary = ContentSummaryFetcher.fetchSummary(sourceUrl) }
                        } else item
                    }
                }.awaitAll()
                
                // Write back the JSON with summaries
                val jsonFile = typeExtractedDir.walk()
                    .filter { it.isFile && it.name.endsWith(".json") && !it.name.equals("version.txt") }
                    .sortedByDescending { it.name.startsWith("polished_") }
                    .firstOrNull()
                
                if (jsonFile != null) {
                    val updatedReport = report.copy(news = updatedItems)
                    jsonFile.writeText(gson.toJson(updatedReport))
                }
            }
            // -----------------------------------------------------------

            cleanupOldArchives()
            return@withContext true
        } catch (e: Exception) {
            Log.e("ReportRepository", "Error updating $type", e)
            return@withContext false
        }
    }

    private fun cleanupOldArchives() {
        val now = System.currentTimeMillis()
        val threeDaysMillis = 3L * 24 * 60 * 60 * 1000
        dataDir.listFiles()?.forEach { file ->
            if (file.name.endsWith(".zip")) {
                if (now - file.lastModified() > threeDaysMillis) file.delete()
            }
        }
    }

    fun getLocalReport(type: String): PolishedReport {
        val typeDir = File(extractedDir, type)
        if (typeDir.exists()) {
            val jsonFiles = typeDir.walk()
                .filter { it.isFile && it.name.endsWith(".json") && !it.name.equals("version.txt") }
                .toList()
            val jsonFile = jsonFiles.sortedByDescending { it.name.startsWith("polished_") }.firstOrNull()
                
            if (jsonFile != null) {
                try {
                    val jsonContent = jsonFile.readText()
                    val report = gson.fromJson(jsonContent, PolishedReport::class.java)
                    val updatedNews = report.news.map { item ->
                        if (!item.imagePath.isNullOrEmpty()) {
                            val imgFile = File(typeDir, item.imagePath)
                            item.apply { localImageFile = imgFile }
                        } else item
                    }
                    return report.copy(news = updatedNews)
                } catch (e: Exception) {
                    e.printStackTrace()
                }
            }
        }
        return PolishedReport()
    }
}
