package com.example.postgarden.data

import com.google.gson.annotations.SerializedName

data class PolishedReport(
    @SerializedName("timestamp") val timestamp: String? = null,
    @SerializedName("news") val news: List<PolishedNewsItem> = emptyList()
)
