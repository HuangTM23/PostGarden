package com.example.postgarden.data

import android.content.Context
import android.util.Log
import com.google.gson.Gson
import kotlinx.coroutines.Dispatchers
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
    
    // Directory structure: filesDir/extracted/{type}/
    private val extractedRoot = File(context.filesDir, "extracted")

    fun getCachedReports(): List<CachedReport> {
        val list = mutableListOf<CachedReport>()
        val types = listOf("home", "world", "entertainment")
        for (type in types) {
            val typeDir = File(extractedRoot, type)
            val versionFile = File(typeDir, "version.txt")
            if (typeDir.exists() && versionFile.exists()) {
                 list.add(CachedReport(type, versionFile.readText().trim(), versionFile.lastModified()))
            }
        }
        return list
    }

    fun isVersionCached(type: String, zipFilename: String): Boolean {
        // We use the zipFilename (which includes timestamp) to verify cache
        // Simple check: Is there a marker file or does the directory exist and match expectation?
        // Since we extract to 'extracted/home/', we need to know WHICH version is there.
        // We can store a 'version.txt' inside the extracted dir.
        val typeDir = File(extractedRoot, type)
        val versionFile = File(typeDir, "version.txt")
        if (typeDir.exists() && versionFile.exists()) {
            val cachedVersion = versionFile.readText().trim()
            return cachedVersion == zipFilename
        }
        return false
    }

    suspend fun downloadAndExtract(type: String, zipFilename: String): Boolean = withContext(Dispatchers.IO) {
        val url = "${ApiClient.BASE_URL}/$zipFilename"
        val typeDir = File(extractedRoot, type)
        
        // 1. Download ZIP to temp file
        val tempZip = File(context.cacheDir, "temp_$type.zip")
        val request = Request.Builder().url(url).build()
        
        try {
            val response = client.newCall(request).execute()
            if (!response.isSuccessful) return@withContext false
            
            val source = response.body?.byteStream() ?: return@withContext false
            tempZip.outputStream().use { output ->
                source.copyTo(output)
            }
            
            // 2. Clear old data
            if (typeDir.exists()) {
                typeDir.deleteRecursively()
            }
            typeDir.mkdirs()
            
            // 3. Unzip
            ZipInputStream(BufferedInputStream(tempZip.inputStream())).use { zis ->
                var entry = zis.nextEntry
                while (entry != null) {
                    val file = File(typeDir, entry.name)
                    if (entry.isDirectory) {
                        file.mkdirs()
                    } else {
                        file.parentFile?.mkdirs()
                        FileOutputStream(file).use { fos ->
                            zis.copyTo(fos)
                        }
                    }
                    entry = zis.nextEntry
                }
            }
            
            // 4. Mark version
            File(typeDir, "version.txt").writeText(zipFilename)
            
            // Clean temp
            tempZip.delete()
            return@withContext true
            
        } catch (e: Exception) {
            Log.e("ReportRepository", "Error downloading/extracting zip", e)
            return@withContext false
        }
    }

    fun getLocalReport(type: String): PolishedReport {
        val typeDir = File(extractedRoot, type)
        if (!typeDir.exists()) return PolishedReport()
        
        // Find the JSON file (polished_all_TIMESTAMP.json)
        val jsonFile = typeDir.listFiles()?.find { it.name.startsWith("polished_all_") && it.name.endsWith(".json") }
        
        if (jsonFile != null) {
            try {
                val report = gson.fromJson(jsonFile.readText(), PolishedReport::class.java)
                
                // Update image paths to absolute local paths
                val updatedNews = report.news.map { item ->
                    if (item.imagePath.isNotEmpty()) {
                        val imgFile = File(typeDir, item.imagePath)
                        item.apply { localImageFile = imgFile }
                    } else {
                        item
                    }
                }
                return report.copy(news = updatedNews)
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
        return PolishedReport()
    }
}
