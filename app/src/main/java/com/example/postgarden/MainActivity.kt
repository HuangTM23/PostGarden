package com.example.postgarden

import android.app.DownloadManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.os.Environment
import android.view.Menu
import android.view.MenuItem
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.postgarden.data.ApiClient
import com.example.postgarden.data.PolishedNewsItem
import com.example.postgarden.data.ReportRepository
import com.example.postgarden.ui.HistoryActivity
import com.example.postgarden.ui.NewsAdapter
import com.google.android.material.floatingactionbutton.FloatingActionButton
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.launch
import java.io.File

class MainActivity : AppCompatActivity() {

    private lateinit var tvStatus: TextView
    private lateinit var rvNews: RecyclerView
    private lateinit var newsAdapter: NewsAdapter
    private val apiClient = ApiClient()
    private lateinit var repository: ReportRepository
    
    // Track what is currently being viewed
    private var currentReportType: String = "morning" // Default
    
    private val historyLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        if (result.resultCode == RESULT_OK) {
            val path = result.data?.getStringExtra("selected_file_path")
            if (path != null) {
                val file = File(path)
                loadReportFromFile(file)
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        tvStatus = findViewById(R.id.tvStatus)
        rvNews = findViewById(R.id.rvNews)
        val fabRefresh = findViewById<FloatingActionButton>(R.id.fabRefresh)
        
        newsAdapter = NewsAdapter()
        repository = ReportRepository(this)

        rvNews.layoutManager = LinearLayoutManager(this)
        rvNews.adapter = newsAdapter

        fabRefresh.setOnClickListener {
            fetchLatestReports()
        }

        // Load latest if available
        val latest = repository.getLatestReport()
        if (latest != null && latest.isNotEmpty()) {
             displayReport(latest)
             val latestFile = repository.getHistoryFiles().firstOrNull()
             if (latestFile != null) {
                 updateCurrentTypeFromFile(latestFile)
             }
        } else {
            tvStatus.text = "No reports found. Click button to refresh."
        }
    }

    override fun onCreateOptionsMenu(menu: Menu?): Boolean {
        menuInflater.inflate(R.menu.main_menu, menu)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            R.id.action_history -> {
                val intent = Intent(this, HistoryActivity::class.java)
                historyLauncher.launch(intent)
                true
            }
            R.id.action_save_zip -> {
                downloadZipReport(currentReportType)
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }

    private fun updateCurrentTypeFromFile(file: File) {
        val name = file.name
        if (name.contains("morning")) {
            currentReportType = "morning"
        } else if (name.contains("evening")) {
            currentReportType = "evening"
        }
    }

    private fun loadReportFromFile(file: File) {
        val items = repository.loadReport(file)
        displayReport(items)
        updateCurrentTypeFromFile(file)
        Toast.makeText(this, "Loaded: ${file.name}", Toast.LENGTH_SHORT).show()
    }

    private fun fetchLatestReports() {
        tvStatus.text = "Fetching latest reports..."
        lifecycleScope.launch {
            try {
                val morningDeferred = async { apiClient.fetchRaw("morning") }
                val eveningDeferred = async { apiClient.fetchRaw("evening") }

                val (morningJson, eveningJson) = awaitAll(morningDeferred, eveningDeferred)

                var foundAny = false
                if (morningJson != null) {
                    repository.saveReport("morning", morningJson)
                    foundAny = true
                }
                if (eveningJson != null) {
                    repository.saveReport("evening", eveningJson)
                    foundAny = true
                }

                if (foundAny) {
                    val latest = repository.getLatestReport()
                    if (latest != null) {
                        displayReport(latest)
                        val latestFile = repository.getHistoryFiles().firstOrNull()
                        if (latestFile != null) updateCurrentTypeFromFile(latestFile)
                    }
                    tvStatus.text = "Fetch complete."
                } else {
                    tvStatus.text = "No new reports found on server."
                }

            } catch (e: Exception) {
                tvStatus.text = "Error fetching: ${e.message}"
                e.printStackTrace()
            }
        }
    }

    private fun displayReport(items: List<PolishedNewsItem>) {
        if (items.isEmpty()) {
            tvStatus.text = "Report is empty."
            newsAdapter.submitList(emptyList())
            return
        }

        val newsItemsForDisplay = items.filter { it.rank > 0 }
        newsAdapter.submitList(newsItemsForDisplay)

        val summary = items.find { it.rank == 0 }
        if (summary != null) {
            tvStatus.text = "${summary.title}\n\n${summary.content}"
        } else {
            tvStatus.text = "Report loaded."
        }
    }

    private fun downloadZipReport(reportType: String) {
        val zipFileName = "${reportType}_report.zip"
        val downloadUrl = "${ApiClient.BASE_URL}/$zipFileName"
        
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
            Toast.makeText(this, "Starting download: $zipFileName", Toast.LENGTH_SHORT).show()
        } catch (e: Exception) {
            Toast.makeText(this, "Download failed: ${e.message}", Toast.LENGTH_LONG).show()
            e.printStackTrace()
        }
    }
}
