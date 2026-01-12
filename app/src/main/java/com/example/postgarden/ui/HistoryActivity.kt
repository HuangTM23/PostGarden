package com.example.postgarden.ui

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.postgarden.R
import com.example.postgarden.data.ReadHistoryRepository

class HistoryActivity : AppCompatActivity() {

    private lateinit var repository: ReadHistoryRepository
    private lateinit var adapter: HistoryAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_history)
        title = "阅读历史"

        repository = ReadHistoryRepository(this)
        
        val rvHistory = findViewById<RecyclerView>(R.id.rvHistory)
        rvHistory.layoutManager = LinearLayoutManager(this)
        
        adapter = HistoryAdapter { item ->
            // Open the history item (url) directly in WebView
            if (item.url.isNotEmpty()) {
                val intent = Intent(this, WebViewActivity::class.java).apply {
                    putExtra("url", item.url)
                    putExtra("title", item.title)
                }
                startActivity(intent)
            }
        }
        
        rvHistory.adapter = adapter
        
        loadHistory()
    }

    private fun loadHistory() {
        val historyItems = repository.getHistory()
        adapter.submitList(historyItems)
    }
}
