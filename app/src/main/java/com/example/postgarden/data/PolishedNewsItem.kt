package com.example.postgarden.data

import com.google.gson.annotations.SerializedName
import java.io.File

data class PolishedNewsItem(
    @SerializedName("rank") val rank: Int = 0,
    @SerializedName("title") val title: String? = "",
    @SerializedName("original_title") val originalTitle: String? = "",
    @SerializedName("content") val content: String? = "",
    @SerializedName("source_platform") val sourcePlatform: String? = "",
    @SerializedName("source_url") val sourceUrl: String? = "",
    @SerializedName("image") val imagePath: String? = "",
    @SerializedName("summary") var summary: String? = ""
) {
    // This will be set dynamically after parsing to point to local file
    var localImageFile: File? = null

    val fullImageUrl: Any
        get() = localImageFile ?: (imagePath ?: "")
}