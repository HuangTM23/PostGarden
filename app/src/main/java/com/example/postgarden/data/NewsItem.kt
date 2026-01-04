package com.example.postgarden.data

data class NewsItem(
    val rank: Int,
    val title: String,
    val description: String,
    val sourcePlatform: String,
    val sourceUrl: String,
    val imageUrl: String,
    val hotScore: String
)
