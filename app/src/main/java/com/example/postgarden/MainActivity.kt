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
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import android.app.Activity

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
    private lateinit var progressBar: android.widget.ProgressBar

    private val historyLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            val type = result.data?.getStringExtra("selected_type")
            if (type != null) {
                currentReportType = type
                when(type) {
                    "home" -> bottomNavigationView.selectedItemId = R.id.nav_home
                    "world" -> bottomNavigationView.selectedItemId = R.id.nav_international
                    "entertainment" -> bottomNavigationView.selectedItemId = R.id.nav_entertainment
                }
                loadLocalData()
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        toolbar = findViewById(R.id.toolbar)
        setSupportActionBar(toolbar)
        
        progressBar = findViewById(R.id.progressBar)

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
                manualRefresh()
            }
        }

        bottomNavigationView.setOnItemSelectedListener { item ->
            when (item.itemId) {
                R.id.nav_home -> {
                    currentReportType = "home"
                    if (!loadLocalData()) {
                        manualRefresh() // Auto fetch if empty
                    }
                    true
                }
                R.id.nav_international -> {
                    currentReportType = "world"
                    if (!loadLocalData()) {
                        manualRefresh()
                    }
                    true
                }
                R.id.nav_entertainment -> {
                    currentReportType = "entertainment"
                    if (!loadLocalData()) {
                        manualRefresh()
                    }
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
        
        // 1. Show Local Data Immediately
        if (!loadLocalData()) {
            // First run or empty cache
            progressBar.visibility = android.view.View.VISIBLE
        }
        
        // 2. Start Background Update
        startBackgroundUpdate()
    }

    private fun loadLocalData(): Boolean {
        val report = repository.getLocalReport(currentReportType)
        if (report.news.isNotEmpty()) {
            displayReport(report.news)
            return true
        } else {
            // Explicitly clear adapter to avoid showing stale data from previous tab
            newsAdapter.submitList(emptyList())
            Toast.makeText(this, "暂无本地数据", Toast.LENGTH_SHORT).show()
            return false
        }
    }

    private fun startBackgroundUpdate() {
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                // 1. Fetch Server Versions
                val serverVersions = apiClient.fetchLatestVersions() ?: run {
                    withContext(Dispatchers.Main) { 
                        progressBar.visibility = android.view.View.GONE
                        Toast.makeText(this@MainActivity, "无法连接服务器，请检查网络", Toast.LENGTH_SHORT).show()
                    }
                    return@launch
                }
                
                // 2. Load Local Versions for comparison
                val localVersions = repository.getLocalVersions()
                
                // 3. Determine if update is needed
                val needsUpdate = localVersions == null ||
                        serverVersions.home != localVersions.home ||
                        serverVersions.world != localVersions.world ||
                        serverVersions.entertainment != localVersions.entertainment
                
                if (needsUpdate) {
                    // Update latestVersions variable for UI tracking
                    latestVersions = serverVersions
                    
                    // 4. Download ALL ZIPs in parallel
                    val types = mapOf(
                        "home" to serverVersions.home,
                        "world" to serverVersions.world,
                        "entertainment" to serverVersions.entertainment
                    )
                    
                    val deferreds = types.map { (type, version) ->
                        async {
                            if (version != null) {
                                repository.downloadAndPrepare(type, version)
                            } else true
                        }
                    }
                    
                    val results = deferreds.awaitAll()
                    val allSuccess = results.all { it }
                    
                    if (allSuccess) {
                        // 5. Atomic switch: Save local version index
                        repository.saveLocalVersions(serverVersions)
                        
                        withContext(Dispatchers.Main) {
                            loadLocalData()
                            Toast.makeText(this@MainActivity, "内容已同步最新", Toast.LENGTH_SHORT).show()
                        }
                    }
                }
                
                withContext(Dispatchers.Main) {
                    progressBar.visibility = android.view.View.GONE
                }
                
            } catch (e: Exception) {
                e.printStackTrace()
                withContext(Dispatchers.Main) { progressBar.visibility = android.view.View.GONE }
            }
        }
    }
    
    private fun manualRefresh() {
        val fabRefresh = findViewById<FloatingActionButton>(R.id.fabRefresh)
        isRefreshing = true
        fabRefresh.isEnabled = false 
        fabRefresh.setImageResource(R.drawable.ic_refresh)
        progressBar.visibility = android.view.View.VISIBLE
        
        lifecycleScope.launch {
            // Re-use background update logic for simplicity and consistency
            startBackgroundUpdate()
            
            kotlinx.coroutines.delay(1500)
            fabRefresh.setImageResource(R.drawable.ic_refresh) 
            fabRefresh.isEnabled = true 
            isRefreshing = false
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
    
    // fetchLatestReports is removed, logic moved to startBackgroundUpdate and manualRefresh
    
    private fun displayReport(items: List<PolishedNewsItem>) {
        if (items.isEmpty()) {
            newsAdapter.submitList(emptyList())
            return
        }

        val newsItemsForDisplay = items.filter { it.rank > 0 }
        newsAdapter.submitList(newsItemsForDisplay) {
            rvNews.scrollToPosition(0)
        }

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
