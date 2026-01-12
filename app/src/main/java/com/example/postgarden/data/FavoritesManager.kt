package com.example.postgarden.data

import android.content.Context
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import java.io.File

class FavoritesManager(private val context: Context) {
    private val favoritesFile = File(context.filesDir, "app_favorites.json")
    private val imagesDir = File(context.filesDir, "app_favorites_images").apply { mkdirs() }
    private val gson = Gson()
    private val mutex = Mutex()

    // Cache in memory to reduce IO
    private var memoryCache: MutableList<PolishedNewsItem>? = null

    suspend fun getFavorites(): List<PolishedNewsItem> {
        return mutex.withLock {
            if (memoryCache != null) {
                return@withLock memoryCache!!.toList()
            }
            loadFromFile()
        }
    }

    suspend fun isFavorite(url: String?): Boolean {
        if (url.isNullOrEmpty()) return false
        val list = getFavorites() // Thread-safe access
        return list.any { it.sourceUrl == url }
    }

    suspend fun addFavorite(item: PolishedNewsItem): Boolean {
        return withContext(Dispatchers.IO) {
            mutex.withLock {
                // Ensure cache is loaded
                if (memoryCache == null) loadFromFile()
                val currentList = memoryCache!!

                // Check if already exists
                if (currentList.any { it.sourceUrl == item.sourceUrl }) return@withLock false

                // 1. Prepare persistence for image
                var persistentImagePath = item.imagePath
                val sourceUrl = item.fullImageUrl.toString()
                
                // Copy image if it's a local file
                if (!sourceUrl.startsWith("http") && sourceUrl.isNotEmpty()) {
                    try {
                        val sourceFile = File(sourceUrl)
                        if (sourceFile.exists()) {
                            val ext = sourceFile.extension.ifEmpty { "jpg" }
                            val fileName = "fav_${System.currentTimeMillis()}_${item.rank}.$ext"
                            val destFile = File(imagesDir, fileName)
                            sourceFile.copyTo(destFile, overwrite = true)
                            persistentImagePath = destFile.absolutePath
                        }
                    } catch (e: Exception) {
                        e.printStackTrace()
                    }
                }

                // 2. Create new item with updated path
                val newItem = item.copy(imagePath = persistentImagePath)
                // Need to set localImageFile manually because copy() doesn't handle it (it's not in constructor)
                if (persistentImagePath != null) {
                    newItem.localImageFile = File(persistentImagePath)
                }

                // 3. Add to list and save
                currentList.add(0, newItem) // Add to top
                saveToFile(currentList)
                true
            }
        }
    }

    suspend fun removeFavorite(item: PolishedNewsItem): Boolean {
        return withContext(Dispatchers.IO) {
            mutex.withLock {
                if (memoryCache == null) loadFromFile()
                val currentList = memoryCache!!

                val existingItem = currentList.find { it.sourceUrl == item.sourceUrl }
                if (existingItem != null) {
                    // 1. Delete local image if needed
                    val imgPath = existingItem.imagePath
                    if (!imgPath.isNullOrEmpty() && imgPath.contains("app_favorites_images")) {
                        try {
                            val file = File(imgPath)
                            if (file.exists()) file.delete()
                        } catch (e: Exception) { e.printStackTrace() }
                    }

                    // 2. Remove from list and save
                    currentList.remove(existingItem)
                    saveToFile(currentList)
                    true // Removed
                } else {
                    false // Was not in favorites
                }
            }
        }
    }

    private fun loadFromFile(): List<PolishedNewsItem> {
        return try {
            if (!favoritesFile.exists()) {
                memoryCache = mutableListOf()
                return emptyList()
            }
            val json = favoritesFile.readText()
            val type = object : TypeToken<List<PolishedNewsItem>>() {}.type
            val list: List<PolishedNewsItem>? = gson.fromJson(json, type)
            memoryCache = list?.toMutableList() ?: mutableListOf()
            
            // Re-hydrate localImageFile for convenience
            memoryCache?.forEach { 
                if (!it.imagePath.isNullOrEmpty()) {
                    it.localImageFile = File(it.imagePath)
                }
            }
            
            memoryCache!!
        } catch (e: Exception) {
            e.printStackTrace()
            memoryCache = mutableListOf()
            emptyList()
        }
    }

    private fun saveToFile(list: List<PolishedNewsItem>) {
        try {
            val json = gson.toJson(list)
            favoritesFile.writeText(json)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }
}
