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
import com.example.postgarden.data.FavoriteRepository
import com.example.postgarden.ui.HistoryActivity
import com.example.postgarden.ui.NewsAdapter
import com.google.android.material.floatingactionbutton.FloatingActionButton
import com.google.android.material.appbar.MaterialToolbar
import com.google.android.material.bottomnavigation.BottomNavigationView
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.launch
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MainActivity : AppCompatActivity() {

    private lateinit var rvNews: RecyclerView
    private lateinit var newsAdapter: NewsAdapter
    private val apiClient = ApiClient()
    private lateinit var repository: ReportRepository
    private lateinit var favRepository: FavoriteRepository
    private lateinit var toolbar: MaterialToolbar
    private lateinit var bottomNavigationView: BottomNavigationView
    
    // Track what is currently being viewed
    private var currentReportType: String = "morning" // Default
    private var currentServerTimestamp: String? = null // Captured from JSON
    
    // For refresh button animation
    private var isRefreshing = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        toolbar = findViewById(R.id.toolbar)
        setSupportActionBar(toolbar)

        rvNews = findViewById(R.id.rvNews)
        val fabRefresh = findViewById<FloatingActionButton>(R.id.fabRefresh)
        bottomNavigationView = findViewById(R.id.bottomNavigationView)
        
        repository = ReportRepository(this)
        favRepository = FavoriteRepository(this)

        newsAdapter = NewsAdapter(
            onFavoriteClick = { item ->
                val isAdded = favRepository.toggleFavorite(item)
                if (isAdded) {
                    Toast.makeText(this@MainActivity, "已加入收藏", Toast.LENGTH_SHORT).show()
                } else {
                    Toast.makeText(this@MainActivity, "已取消收藏", Toast.LENGTH_SHORT).show()
                    // If we are in favorites view, refresh the list immediately
                    if (bottomNavigationView.selectedItemId == R.id.nav_favorites) {
                        displayReport(favRepository.getFavorites())
                    }
                }
            },
            isFavoriteCheck = { item -> favRepository.isFavorite(item) }
        )

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
                    currentReportType = "morning"
                    loadLatestReport()
                    true
                }
                R.id.nav_international -> {
                    Toast.makeText(this@MainActivity, "国际新闻功能开发中...", Toast.LENGTH_SHORT).show()
                    true
                }
                R.id.nav_entertainment -> {
                    Toast.makeText(this@MainActivity, "娱乐新闻功能开发中...", Toast.LENGTH_SHORT).show()
                    true
                }
                R.id.nav_favorites -> {
                    val favs = favRepository.getFavorites()
                    displayReport(favs)
                    Toast.makeText(this@MainActivity, "收藏夹", Toast.LENGTH_SHORT).show()
                    true
                }
                else -> false
            }
        }
        
        loadLatestReport()
    }

    private fun loadLatestReport() {
        val latest = repository.getLatestReport()
        if (latest.news.isNotEmpty()) {
             currentServerTimestamp = latest.timestamp
             displayReport(latest.news)
             val latestFile = repository.getHistoryFiles().firstOrNull()
             if (latestFile != null) {
                 updateCurrentTypeFromFile(latestFile)
             }
        } else {
            Toast.makeText(this@MainActivity, "暂无新闻，请点击刷新。", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onCreateOptionsMenu(menu: Menu?): Boolean {
        menuInflater.inflate(R.menu.main_menu, menu)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            R.id.action_save_zip -> {
                downloadZipReport()
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

    private fun fetchLatestReports() {
        Toast.makeText(this@MainActivity, "正在获取最新新闻...", Toast.LENGTH_SHORT).show()
        lifecycleScope.launch {
            val fabRefresh = findViewById<FloatingActionButton>(R.id.fabRefresh)
            isRefreshing = true
            fabRefresh.isEnabled = false 
            fabRefresh.setImageResource(R.drawable.ic_refresh) 

            try {
                val morningDeferred = async { apiClient.getReport("morning") }
                val eveningDeferred = async { apiClient.getReport("evening") }

                val reports = awaitAll(morningDeferred, eveningDeferred)
                val morningReport = reports[0]
                val eveningReport = reports[1]

                var foundAny = false
                if (morningReport.news.isNotEmpty()) {
                    // Re-serialize back to JSON to save locally (simplified)
                    val gson = com.google.gson.Gson()
                    repository.saveReport("morning", gson.toJson(morningReport))
                    foundAny = true
                }
                if (eveningReport.news.isNotEmpty()) {
                    val gson = com.google.gson.Gson()
                    repository.saveReport("evening", gson.toJson(eveningReport))
                    foundAny = true
                }

                if (foundAny) {
                    val latest = repository.getLatestReport()
                    if (latest.news.isNotEmpty()) {
                        currentServerTimestamp = latest.timestamp
                        displayReport(latest.news)
                        val latestFile = repository.getHistoryFiles().firstOrNull()
                        if (latestFile != null) updateCurrentTypeFromFile(latestFile)
                    }
                    Toast.makeText(this@MainActivity, "获取成功！", Toast.LENGTH_SHORT).show()
                    fabRefresh.setImageResource(R.drawable.ic_check_green) // Success icon
                    kotlinx.coroutines.delay(1500) 
                } else {
                    Toast.makeText(this@MainActivity, "未发现新报告。", Toast.LENGTH_SHORT).show()
                }

            } catch (e: Exception) {
                Toast.makeText(this@MainActivity, "错误: ${e.message}", Toast.LENGTH_LONG).show()
                e.printStackTrace()
            } finally {
                fabRefresh.setImageResource(R.drawable.ic_refresh) 
                fabRefresh.isEnabled = true 
                isRefreshing = false
            }
        }
    }

    private fun displayReport(items: List<PolishedNewsItem>) {
        if (items.isEmpty()) {
            Toast.makeText(this@MainActivity, "报告内容为空。", Toast.LENGTH_SHORT).show()
            newsAdapter.submitList(emptyList())
            return
        }

        val newsItemsForDisplay = items.filter { it.rank > 0 }
        newsAdapter.submitList(newsItemsForDisplay)

        val summary = items.find { it.rank == 0 }
        if (summary != null) {
            Toast.makeText(this@MainActivity, "今日摘要: ${summary.title}", Toast.LENGTH_LONG).show()
        }
    }

    private fun downloadZipReport() {
        val timestamp = currentServerTimestamp
        if (timestamp == null) {
            Toast.makeText(this, "无法获取报告时间戳，下载失败。", Toast.LENGTH_SHORT).show()
            return
        }
        
        val zipName = "SampleNews_${timestamp}.zip"
        val downloadUrl = "${ApiClient.BASE_URL}/$zipName"
        
        try {
            val request = DownloadManager.Request(Uri.parse(downloadUrl))
                .setTitle(zipName)
                .setDescription("Downloading $zipName from PostGarden.")
                .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                .setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, zipName)
                .setRequiresCharging(false)
                .setAllowedOverMetered(true)
                .setAllowedOverRoaming(true)

            val downloadManager = getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
            downloadManager.enqueue(request)
            Toast.makeText(this, "开始下载: $zipName", Toast.LENGTH_SHORT).show()
        } catch (e: Exception) {
            Toast.makeText(this, "下载失败: ${e.message}", Toast.LENGTH_LONG).show()
            e.printStackTrace()
        }
    }
}
