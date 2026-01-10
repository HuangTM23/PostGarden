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
    
    // Directory structure: /Android/data/package/files/PostGarden/data/
    // Use getExternalFilesDir to make it accessible to user (and visible in file manager)
    private val rootDir = context.getExternalFilesDir(null) ?: context.filesDir
    private val baseDir = File(rootDir, "PostGarden")
    private val dataDir = File(baseDir, "data")
    private val extractedDir = File(dataDir, "extracted")
    private val localVersionFile = File(dataDir, "latest_versions.json")

    init {
        Log.d("ReportRepository", "Storage Path: ${dataDir.absolutePath}")
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

    fun getCachedReports(): List<CachedReport> {
        val list = mutableListOf<CachedReport>()
        val types = listOf("home", "world", "entertainment")
        for (type in types) {
            val typeDir = File(extractedDir, type)
            val versionFile = File(typeDir, "version.txt")
            if (typeDir.exists() && versionFile.exists()) {
                val version = versionFile.readText().trim()
                list.add(CachedReport(type, version, versionFile.lastModified()))
            }
        }
        return list
    }

    fun isVersionCached(type: String, zipFilename: String): Boolean {
        val typeDir = File(extractedDir, type)
        val versionFile = File(typeDir, "version.txt")
        return versionFile.exists() && versionFile.readText().trim() == zipFilename
    }

    suspend fun downloadAndPrepare(type: String, zipFilename: String): Boolean = withContext(Dispatchers.IO) {
        val url = "${ApiClient.BASE_URL}/$zipFilename"
        val zipFile = File(dataDir, zipFilename)
        val typeExtractedDir = File(extractedDir, type)
        
        try {
            // 1. Download to dataDir
            val request = Request.Builder().url(url).build()
            val response = client.newCall(request).execute()
            if (!response.isSuccessful) return@withContext false
            
            val source = response.body?.byteStream() ?: return@withContext false
            zipFile.outputStream().use { output ->
                source.copyTo(output)
            }
            
            // 2. Unzip immediately for UI
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
                        FileOutputStream(file).use { fos ->
                            zis.copyTo(fos)
                        }
                    }
                    entry = zis.nextEntry
                }
            }
            
            // 3. Mark version
            File(typeExtractedDir, "version.txt").writeText(zipFilename)
            
            // 4. Cleanup old archives
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
                if (now - file.lastModified() > threeDaysMillis) {
                    file.delete()
                }
            }
        }
    }

    fun getLocalReport(type: String): PolishedReport {
        val typeDir = File(extractedDir, type)
        Log.d("ReportRepository", "Loading local report for $type from ${typeDir.absolutePath}")
        
        if (typeDir.exists()) {
            // Recursive search for ANY JSON file (except metadata like version.txt or latest_versions.json if they accidentally got there)
            // Prioritize "polished_" but fallback to others
            val jsonFiles = typeDir.walk()
                .filter { it.isFile && it.name.endsWith(".json") && !it.name.equals("version.txt") }
                .toList()
            
            // Sort to try polished_ first
            val jsonFile = jsonFiles.sortedByDescending { it.name.startsWith("polished_") }.firstOrNull()
                
            if (jsonFile != null) {
                Log.d("ReportRepository", "Found JSON: ${jsonFile.name} at ${jsonFile.absolutePath}")
                try {
                    val jsonContent = jsonFile.readText()
                    val report = gson.fromJson(jsonContent, PolishedReport::class.java)
                    
                    if (report.news.isNullOrEmpty()) {
                         Log.e("ReportRepository", "Parsed report but news list is empty/null.")
                    } else {
                        Log.d("ReportRepository", "Parsed ${report.news.size} items")
                    }
                    
                    val updatedNews = report.news.map { item ->
                        if (!item.imagePath.isNullOrEmpty()) {
                            val imgFile = File(typeDir, item.imagePath)
                            item.apply { localImageFile = imgFile }
                        } else item
                    }
                    return report.copy(news = updatedNews)
                } catch (e: Exception) {
                    Log.e("ReportRepository", "Error parsing JSON from ${jsonFile.name}", e)
                    e.printStackTrace()
                }
            } else {
                Log.e("ReportRepository", "No JSON file found in ${typeDir.absolutePath}. Files found: ${typeDir.list()?.joinToString()}")
            }
        } else {
            Log.e("ReportRepository", "Directory not found: ${typeDir.absolutePath}")
        }
        return PolishedReport()
    }
}