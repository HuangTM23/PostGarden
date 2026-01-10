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
    private var currentReportType: String = "home" // Default: home, world, entertainment
    private var latestVersions: com.example.postgarden.data.LatestVersions? = null
    
    // For refresh button animation
    private var isRefreshing = false

    private val historyLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            val type = result.data?.getStringExtra("selected_type")
            if (type != null) {
                when(type) {
                    "home" -> bottomNavigationView.selectedItemId = R.id.nav_home
                    "world" -> bottomNavigationView.selectedItemId = R.id.nav_international
                    "entertainment" -> bottomNavigationView.selectedItemId = R.id.nav_entertainment
                }
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
        
        repository = ReportRepository(this)
        favRepository = FavoriteRepository(this)

        newsAdapter = NewsAdapter(
            onFavoriteClick = { item ->
                val isAdded = favRepository.toggleFavorite(item)
                if (isAdded) {
                    Toast.makeText(this@MainActivity, "已加入收藏", Toast.LENGTH_SHORT).show()
                } else {
                    Toast.makeText(this@MainActivity, "已取消收藏", Toast.LENGTH_SHORT).show()
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
                    currentReportType = "home"
                    loadLocalOrFetch()
                    true
                }
                R.id.nav_international -> {
                    currentReportType = "world"
                    loadLocalOrFetch()
                    true
                }
                R.id.nav_entertainment -> {
                    currentReportType = "entertainment"
                    loadLocalOrFetch()
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
        
        // Initial load
        fetchLatestReports()
    }

    private fun loadLocalOrFetch() {
        val report = repository.getLocalReport(currentReportType)
        if (report.news.isNotEmpty()) {
            displayReport(report.news)
        } else {
            // If local is empty, try to fetch
            fetchLatestReports()
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
                downloadZipReport()
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }

    private fun fetchLatestReports() {
        if (isRefreshing) return
        
        Toast.makeText(this@MainActivity, "正在检查更新...", Toast.LENGTH_SHORT).show()
        lifecycleScope.launch {
            val fabRefresh = findViewById<FloatingActionButton>(R.id.fabRefresh)
            isRefreshing = true
            fabRefresh.isEnabled = false 
            fabRefresh.setImageResource(R.drawable.ic_refresh) 

            try {
                // 1. Fetch Version Index
                val versions = apiClient.fetchLatestVersions()
                latestVersions = versions
                
                if (versions != null) {
                    // 2. Check and Download for current type (or all if desired, here just current for speed)
                    // We can also trigger background sync for others.
                    
                    val targetZip = when(currentReportType) {
                        "home" -> versions.home
                        "world" -> versions.world
                        "entertainment" -> versions.entertainment
                        else -> null
                    }
                    
                    if (targetZip != null) {
                        if (!repository.isVersionCached(currentReportType, targetZip)) {
                            Toast.makeText(this@MainActivity, "发现新版本，正在下载...", Toast.LENGTH_SHORT).show()
                            val success = repository.downloadAndExtract(currentReportType, targetZip)
                            if (success) {
                                Toast.makeText(this@MainActivity, "更新完成", Toast.LENGTH_SHORT).show()
                            } else {
                                Toast.makeText(this@MainActivity, "下载失败", Toast.LENGTH_SHORT).show()
                            }
                        } else {
                            // Already latest
                        }
                        
                        // 3. Display
                        val report = repository.getLocalReport(currentReportType)
                        displayReport(report.news)
                        fabRefresh.setImageResource(R.drawable.ic_check_green)
                    } else {
                         Toast.makeText(this@MainActivity, "当前板块暂无数据", Toast.LENGTH_SHORT).show()
                    }
                } else {
                    Toast.makeText(this@MainActivity, "无法获取版本信息", Toast.LENGTH_SHORT).show()
                }

            } catch (e: Exception) {
                Toast.makeText(this@MainActivity, "错误: ${e.message}", Toast.LENGTH_LONG).show()
                e.printStackTrace()
            } finally {
                kotlinx.coroutines.delay(1000)
                fabRefresh.setImageResource(R.drawable.ic_refresh) 
                fabRefresh.isEnabled = true 
                isRefreshing = false
            }
        }
    }

    private fun displayReport(items: List<PolishedNewsItem>) {
        if (items.isEmpty()) {
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
        val versions = latestVersions ?: return
        val targetZip = when(currentReportType) {
            "home" -> versions.home
            "world" -> versions.world
            "entertainment" -> versions.entertainment
            else -> null
        }
        
        if (targetZip == null) {
            Toast.makeText(this, "暂无文件可下载", Toast.LENGTH_SHORT).show()
            return
        }
        
        val downloadUrl = "${ApiClient.BASE_URL}/$targetZip"
        
        try {
            val request = DownloadManager.Request(Uri.parse(downloadUrl))
                .setTitle(targetZip)
                .setDescription("Downloading $currentReportType news report from PostGarden.")
                .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                .setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, targetZip)
                .setAllowedOverMetered(true)
                .setAllowedOverRoaming(true)

            val downloadManager = getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
            downloadManager.enqueue(request)
            Toast.makeText(this, "开始下载: $targetZip", Toast.LENGTH_SHORT).show()
        } catch (e: Exception) {
            Toast.makeText(this, "下载失败: ${e.message}", Toast.LENGTH_LONG).show()
            e.printStackTrace()
        }
    }
}
