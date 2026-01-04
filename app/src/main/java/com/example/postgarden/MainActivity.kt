package com.example.postgarden

import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.postgarden.data.ApiClient
import com.example.postgarden.data.PolishedNewsItem
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    private lateinit var tvStatus: TextView
    private lateinit var tvContent: TextView
    private val apiClient = ApiClient()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        tvStatus = findViewById(R.id.tvStatus)
        tvContent = findViewById(R.id.tvContent)
        val btnFetchMorning = findViewById<Button>(R.id.btnFetchMorning)
        val btnFetchEvening = findViewById<Button>(R.id.btnFetchEvening)

        btnFetchMorning.setOnClickListener {
            fetchReport("morning")
        }

        btnFetchEvening.setOnClickListener {
            fetchReport("evening")
        }
    }

    private fun fetchReport(reportType: String) {
        tvStatus.text = "Fetching ${reportType.capitalize()} report..."
        tvContent.text = ""

        lifecycleScope.launch {
            try {
                val items = apiClient.getReport(reportType)
                displayReport(items)
            } catch (e: Exception) {
                tvStatus.text = "Error: ${e.message}"
                e.printStackTrace()
            }
        }
    }

    private fun displayReport(items: List<PolishedNewsItem>) {
        if (items.isEmpty()) {
            tvStatus.text = "Failed to fetch report or no items found."
            return
        }

        val sb = StringBuilder()
        val summary = items.find { it.rank == 0 }

        if (summary != null) {
            tvStatus.text = "Report for: ${summary.title}"
            sb.append("=== ${summary.title} ===\n\n")
        } else {
            tvStatus.text = "Done: ${items.size} items."
        }

        items.filter { it.rank > 0 }.forEach { item ->
            sb.append("${item.rank}. ${item.title}\n")
            sb.append("   ${item.content}\n")
            sb.append("   [Source: ${item.source_platform}]\n\n")
        }
        tvContent.text = sb.toString()
    }
}
