package com.example.postgarden.data

import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import org.junit.Assert.assertEquals
import org.junit.Test

class JsonParsingTest {

    @Test
    fun testParsePolishedNews() {
        val json = """
            {
              "news": [
                {
                  "rank": 0,
                  "title": "Summary Title",
                  "content": "Summary Content",
                  "image": ""
                },
                {
                  "rank": 1,
                  "title": "News Title 1",
                  "content": "Content 1",
                  "source_platform": "Baidu",
                  "source_url": "http://baidu.com",
                  "image": "images/1.jpg"
                }
              ]
            }
        """

        val gson = Gson()
        val type = object : TypeToken<Map<String, List<PolishedNewsItem>>>() {}.type
        val resultMap: Map<String, List<PolishedNewsItem>> = gson.fromJson(json, type)
        val newsList = resultMap["news"] ?: emptyList()

        assertEquals(2, newsList.size)
        
        val summary = newsList[0]
        assertEquals(0, summary.rank)
        assertEquals("Summary Title", summary.title)
        
        val item1 = newsList[1]
        assertEquals(1, item1.rank)
        assertEquals("Baidu", item1.source_platform)
        assertEquals("images/1.jpg", item1.image)
    }
}
