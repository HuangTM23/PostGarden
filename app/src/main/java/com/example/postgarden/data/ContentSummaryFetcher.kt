package com.example.postgarden.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.jsoup.Jsoup

object ContentSummaryFetcher {
    
    suspend fun fetchSummary(url: String?): String = withContext(Dispatchers.IO) {
        if (url.isNullOrEmpty()) return@withContext ""
        
        try {
            val doc = Jsoup.connect(url)
                .userAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
                .timeout(5000)
                .get()

            var summary = doc.select("meta[name=description]").attr("content")
            if (summary.isNullOrEmpty()) {
                summary = doc.select("p").first()?.text() ?: ""
            }
            
            if (summary.isNotEmpty()) {
                val sentences = summary.split(Regex("(?<=[.!?])\\s+"))
                val words = summary.split(" ")
                
                summary = when {
                    sentences.size > 3 -> sentences.take(3).joinToString(" ")
                    words.size > 50 -> words.take(50).joinToString(" ") + "..."
                    else -> summary
                }
            } else {
                summary = "No preview available."
            }
            summary
        } catch (e: Exception) {
            "Preview unavailable."
        }
    }
}
