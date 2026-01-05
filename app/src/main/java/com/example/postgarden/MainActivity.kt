package com.example.postgarden

import android.app.DownloadManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.os.Environment
import android.view.Menu
import android.view.MenuItem
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
import com.google.android.material.appbar.MaterialToolbar
import com.google.android.material.bottomnavigation.BottomNavigationView
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.launch
import java.io.File

class MainActivity : AppCompatActivity() {

    private lateinit var rvNews: RecyclerView
    private lateinit var newsAdapter: NewsAdapter
    private val apiClient = ApiClient()
    private lateinit var repository: ReportRepository
    private lateinit var toolbar: MaterialToolbar
    private lateinit var bottomNavigationView: BottomNavigationView
    
    // Track what is currently being viewed
    private var currentReportType: String = "morning" // Default
    
    // For refresh button animation
    private var isRefreshing = false

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

        toolbar = findViewById(R.id.toolbar)
        setSupportActionBar(toolbar)

        rvNews = findViewById(R.id.rvNews)
        val fabRefresh = findViewById<FloatingActionButton>(R.id.fabRefresh)
        bottomNavigationView = findViewById(R.id.bottomNavigationView)
        
        newsAdapter = NewsAdapter()
        repository = ReportRepository(this)

        rvNews.layoutManager = LinearLayoutManager(this)
        rvNews.adapter = newsAdapter

        fabRefresh.setOnClickListener {
            if (!isRefreshing) {
                fetchLatestReports()
            }
        }

        bottomNavigationView.setOnItemSelectedListener { item ->
            when (item.itemId) {
                R.id.nav_home -> {
                    // "国内" corresponds to current general news fetch
                    currentReportType = "morning" // Default for home, could be dynamic
                    fetchLatestReports()
                    true
                }
                R.id.nav_international -> {
                    Toast.makeText(this, "国际新闻功能开发中...", Toast.LENGTH_SHORT).show()
                    true
                }
                R.id.nav_entertainment -> {
                    Toast.makeText(this, "娱乐新闻功能开发中...", Toast.LENGTH_SHORT).show()
                    true
                }
                R.id.nav_favorites -> {
                    Toast.makeText(this, "收藏功能开发中...", Toast.LENGTH_SHORT).show()
                    true
                }
                else -> false
            }
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
            Toast.makeText(this, "No reports found. Click refresh.", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onCreateOptionsMenu(menu: Menu?): Boolean {
        menuInflater.inflate(R.menu.main_menu, menu)
        // Optionally hide history item here if it's completely removed
        menu?.findItem(R.id.action_history)?.isVisible = false
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            R.id.action_save_zip -> {
                downloadZipReport(currentReportType)
                true
            }
            R.id.action_history -> { // Removed from menu, but keeping this for completeness in case it's brought back
                val intent = Intent(this, HistoryActivity::class.java)
                historyLauncher.launch(intent)
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
        // tvStatus.text = "Fetching latest reports..."
        Toast.makeText(this, "Fetching latest reports...", Toast.LENGTH_SHORT).show()
        lifecycleScope.launch {
            val fabRefresh = findViewById<FloatingActionButton>(R.id.fabRefresh)
            isRefreshing = true
            fabRefresh.isEnabled = false // Disable to prevent multiple clicks
            fabRefresh.setImageResource(R.drawable.ic_refresh) // Ensure refresh icon is set

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
                    // tvStatus.text = "Fetch complete."
                    Toast.makeText(this, "Fetch complete.", Toast.LENGTH_SHORT).show()
                    fabRefresh.setImageResource(R.drawable.ic_check_green) // Success icon
                    kotlinx.coroutines.delay(1500) // Show checkmark for 1.5 seconds
                } else {
                    // tvStatus.text = "No new reports found on server."
                    Toast.makeText(this, "No new reports found on server.", Toast.LENGTH_SHORT).show()
                }

            } catch (e: Exception) {
                // tvStatus.text = "Error fetching: ${e.message}"
                Toast.makeText(this, "Error fetching: ${e.message}", Toast.LENGTH_LONG).show()
                e.printStackTrace()
            } finally {
                fabRefresh.setImageResource(R.drawable.ic_refresh) // Revert to refresh icon
                fabRefresh.isEnabled = true // Re-enable button
                isRefreshing = false
            }
        }
    }

    private fun displayReport(items: List<PolishedNewsItem>) {
        if (items.isEmpty()) {
            // tvStatus.text = "Report is empty."
            Toast.makeText(this, "Report is empty.", Toast.LENGTH_SHORT).show()
            newsAdapter.submitList(emptyList())
            return
        }

        val newsItemsForDisplay = items.filter { it.rank > 0 }
        newsAdapter.submitList(newsItemsForDisplay)

        val summary = items.find { it.rank == 0 }
        if (summary != null) {
            // tvStatus.text = "${summary.title}\n\n${summary.content}"
            Toast.makeText(this, "摘要: ${summary.title}", Toast.LENGTH_LONG).show()
        } else {
            // tvStatus.text = "Report loaded."
            Toast.makeText(this, "Report loaded.", Toast.LENGTH_SHORT).show()
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
