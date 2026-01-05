package com.example.postgarden.data

import android.content.Context
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import java.io.File

class FavoriteRepository(context: Context) {
    private val file = File(context.filesDir, "favorites.json")
    private val gson = Gson()

    fun getFavorites(): List<PolishedNewsItem> {
        if (!file.exists()) return emptyList()
        return try {
            val json = file.readText()
            val type = object : TypeToken<List<PolishedNewsItem>>() {}.type
            gson.fromJson(json, type) ?: emptyList()
        } catch (e: Exception) {
            emptyList()
        }
    }

    fun isFavorite(item: PolishedNewsItem): Boolean {
        return getFavorites().any { it.sourceUrl == item.sourceUrl }
    }

    fun toggleFavorite(item: PolishedNewsItem): Boolean {
        val current = getFavorites().toMutableList()
        val existing = current.find { it.sourceUrl == item.sourceUrl }
        
        val isNowFavorite: Boolean
        if (existing != null) {
            current.remove(existing)
            isNowFavorite = false
        } else {
            current.add(item)
            isNowFavorite = true
        }
        
        save(current)
        return isNowFavorite
    }

    private fun save(items: List<PolishedNewsItem>) {
        val json = gson.toJson(items)
        file.writeText(json)
    }
}
