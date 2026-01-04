package com.example.postgarden

import android.app.DownloadManager
import android.content.Context
import android.net.Uri
import android.os.Bundle
import android.os.Environment
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.postgarden.data.ApiClient
import com.example.postgarden.data.PolishedNewsItem
import com.example.postgarden.ui.NewsAdapter
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    private lateinit var tvStatus: TextView
    private lateinit var rvNews: RecyclerView
    private lateinit var newsAdapter: NewsAdapter
    private val apiClient = ApiClient()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        tvStatus = findViewById(R.id.tvStatus)
        rvNews = findViewById(R.id.rvNews)
        newsAdapter = NewsAdapter()

        rvNews.layoutManager = LinearLayoutManager(this)
        rvNews.adapter = newsAdapter

        val btnFetchMorning = findViewById<Button>(R.id.btnFetchMorning)
        val btnFetchEvening = findViewById<Button>(R.id.btnFetchEvening)
        val btnDownloadZip = findViewById<Button>(R.id.btnDownloadZip)

        btnFetchMorning.setOnClickListener {
            fetchReport("morning")
        }

        btnFetchEvening.setOnClickListener {
            fetchReport("evening")
        }

        btnDownloadZip.setOnClickListener {
            downloadZipReport("morning") // Default to morning report for now
        }
    }

    private fun fetchReport(reportType: String) {
        tvStatus.text = "Fetching ${reportType.capitalize()} report..."
        newsAdapter.submitList(emptyList()) // Clear previous list

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
            newsAdapter.submitList(emptyList())
            return
        }

        // Filter out the summary item (rank 0) for the list display
        val newsItemsForDisplay = items.filter { it.rank > 0 }
        newsAdapter.submitList(newsItemsForDisplay)

        // Set status text to summary title
        val summary = items.find { it.rank == 0 }
        tvStatus.text = summary?.title ?: "Report fetched successfully."
    }

    private fun downloadZipReport(reportType: String) {
        val zipFileName = "${reportType}_report.zip"
        val downloadUrl = "${ApiClient.BASE_URL}/$zipFileName" // Access via class name
        
        try {
            val request = DownloadManager.Request(Uri.parse(downloadUrl))
                .setTitle(zipFileName)
                .setDescription("Downloading $reportType news report from PostGarden.")
                .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                .setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, zipFileName)
                .setRequiresCharging(false)
                .setAllowedOverMetered(true)
                .setAllowedOverRoaming(true)

            val downloadManager = getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
            downloadManager.enqueue(request)
            Toast.makeText(this, "开始下载 '$zipFileName'", Toast.LENGTH_SHORT).show()
        } catch (e: Exception) {
            Toast.makeText(this, "下载失败: ${e.message}", Toast.LENGTH_LONG).show()
            e.printStackTrace()
        }
    }
}
