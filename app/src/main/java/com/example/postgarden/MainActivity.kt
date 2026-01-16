package com.example.postgarden

import android.app.AlertDialog
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.drawable.ColorDrawable
import android.net.Uri
import android.os.Bundle
import android.view.Menu
import android.view.MenuItem
import android.view.View
import android.view.ViewGroup
import android.widget.ImageButton
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.postgarden.data.ApiClient
import com.example.postgarden.data.FavoritesManager
import com.example.postgarden.data.PolishedNewsItem
import com.example.postgarden.data.ReadHistoryRepository
import com.example.postgarden.data.ReportRepository
import com.example.postgarden.ui.HistoryAdapter
import com.example.postgarden.ui.NewsAdapter
import com.example.postgarden.ui.WebViewActivity
import com.google.android.material.appbar.MaterialToolbar
import com.google.android.material.bottomnavigation.BottomNavigationView
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

import androidx.swiperefreshlayout.widget.SwipeRefreshLayout
import androidx.core.content.FileProvider
import java.io.File

class MainActivity : AppCompatActivity() {

    private lateinit var rvNews: RecyclerView
    private lateinit var newsAdapter: NewsAdapter
    private val apiClient = ApiClient()
    private lateinit var repository: ReportRepository
    private lateinit var favManager: FavoritesManager 
    private lateinit var toolbar: MaterialToolbar
    private lateinit var bottomNavigationView: BottomNavigationView
    private lateinit var swipeRefreshLayout: SwipeRefreshLayout
    
    // Track what is currently being viewed
    private var currentReportType: String = "home"
    private var latestVersions: com.example.postgarden.data.LatestVersions? = null
    
    // For refresh button animation
    private var isRefreshing = false
    private lateinit var progressBar: android.widget.ProgressBar

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        toolbar = findViewById(R.id.toolbar)
        setSupportActionBar(toolbar)
        
        progressBar = findViewById(R.id.progressBar)

        rvNews = findViewById(R.id.rvNews)
        swipeRefreshLayout = findViewById(R.id.swipeRefreshLayout)
        bottomNavigationView = findViewById(R.id.bottomNavigationView)
        
        repository = ReportRepository(this)
        favManager = FavoritesManager(this)

        newsAdapter = NewsAdapter(
            onFavoriteClick = { item ->
                handleFavoriteClick(item)
            },
            isFavoriteCheck = { false } 
        )

        rvNews.layoutManager = LinearLayoutManager(this)
        rvNews.adapter = newsAdapter

        swipeRefreshLayout.setOnRefreshListener {
            manualRefresh()
        }

        bottomNavigationView.setOnItemSelectedListener { item ->
            try {
                when (item.itemId) {
                    R.id.nav_home -> {
                        currentReportType = "home"
                        if (!loadLocalData()) manualRefresh()
                        true
                    }
                    R.id.nav_international -> {
                        currentReportType = "world"
                        if (!loadLocalData()) manualRefresh()
                        true
                    }
                    R.id.nav_entertainment -> {
                        currentReportType = "entertainment"
                        if (!loadLocalData()) manualRefresh()
                        true
                    }
                    R.id.nav_favorites -> {
                        loadFavorites()
                        true
                    }
                    else -> false
                }
            } catch (e: Exception) {
                e.printStackTrace()
                false
            }
        }
        
        // 1. Show Local Data Immediately
        if (!loadLocalData()) {
            progressBar.visibility = View.VISIBLE
        }
        
        // 2. Start Background Update Automatically
        startBackgroundUpdate()
        
        // 3. Pre-load favorites into memory
        lifecycleScope.launch { favManager.getFavorites() }
    }

    private fun handleFavoriteClick(item: PolishedNewsItem) {
        lifecycleScope.launch {
            try {
                // Determine if we are adding or removing using sourceUrl as unique key
                val isFav = favManager.isFavorite(item.sourceUrl)
                if (isFav) {
                    favManager.removeFavorite(item)
                    Toast.makeText(this@MainActivity, "已取消收藏", Toast.LENGTH_SHORT).show()
                    // If we are currently viewing favorites, refresh the list to remove the item
                    if (bottomNavigationView.selectedItemId == R.id.nav_favorites) {
                        loadFavorites()
                    }
                } else {
                    favManager.addFavorite(item)
                    Toast.makeText(this@MainActivity, "已加入收藏", Toast.LENGTH_SHORT).show()
                }
                
                // Notify adapter that data set might have changed or specific item needs redraw.
                // Since we update the favorite status in the manager, next time we check it will be correct.
                // But for immediate visual feedback of the HEART icon, we rely on the adapter's click listener
                // updating the UI immediately, and here we just sync the backend state.
                // However, to be safe, we can notify data changed to re-bind all ViewHolders with correct favorite state.
                if (bottomNavigationView.selectedItemId != R.id.nav_favorites) {
                     // Get all favorite URLs for quick checking
                    val favs = favManager.getFavorites()
                    val favUrls = favs.mapNotNull { it.sourceUrl }.toSet()
                    newsAdapter.updateFavoriteSet(favUrls)
                }
                
            } catch (e: Exception) {
                e.printStackTrace()
                Toast.makeText(this@MainActivity, "操作失败", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun loadFavorites() {
        lifecycleScope.launch {
            val favs = favManager.getFavorites()
            displayReport(favs)
            swipeRefreshLayout.isRefreshing = false
        }
    }

    private fun loadLocalData(): Boolean {
        val report = repository.getLocalReport(currentReportType)
        if (report.news.isNotEmpty()) {
            displayReport(report.news)
            // Background check for summaries
            lifecycleScope.launch(Dispatchers.IO) {
                if (repository.ensureSummaries(currentReportType)) {
                    withContext(Dispatchers.Main) {
                        // Reload if changed
                        val updated = repository.getLocalReport(currentReportType)
                        displayReport(updated.news)
                    }
                }
            }
            return true
        } else {
            newsAdapter.submitList(emptyList())
            return false
        }
    }

    private fun startBackgroundUpdate() {
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val serverVersions = apiClient.fetchLatestVersions() ?: run {
                    withContext(Dispatchers.Main) { 
                        progressBar.visibility = View.GONE 
                        swipeRefreshLayout.isRefreshing = false
                    }
                    return@launch
                }
                
                val localVersions = repository.getLocalVersions()
                val needsUpdate = localVersions == null ||
                        serverVersions.home != localVersions.home ||
                        serverVersions.world != localVersions.world ||
                        serverVersions.entertainment != localVersions.entertainment
                
                if (needsUpdate) {
                    latestVersions = serverVersions
                    val types = mapOf(
                        "home" to serverVersions.home,
                        "world" to serverVersions.world,
                        "entertainment" to serverVersions.entertainment
                    )
                    
                    val deferreds = types.map { (type, version) ->
                        async { if (version != null) repository.downloadAndPrepare(type, version) else true }
                    }
                    
                    val results = deferreds.awaitAll()
                    if (results.all { it }) {
                        repository.saveLocalVersions(serverVersions)
                        withContext(Dispatchers.Main) {
                            if (bottomNavigationView.selectedItemId != R.id.nav_favorites) {
                                loadLocalData()
                            }
                        }
                    }
                }
                withContext(Dispatchers.Main) { 
                    progressBar.visibility = View.GONE 
                    swipeRefreshLayout.isRefreshing = false
                }
            } catch (e: Exception) {
                e.printStackTrace()
                withContext(Dispatchers.Main) { 
                    progressBar.visibility = View.GONE 
                    swipeRefreshLayout.isRefreshing = false
                }
            }
        }
    }
    
    private fun manualRefresh() {
        if (bottomNavigationView.selectedItemId == R.id.nav_favorites) {
            loadFavorites()
            return
        }
        
        isRefreshing = true
        swipeRefreshLayout.isRefreshing = true
        
        lifecycleScope.launch {
            startBackgroundUpdate()
            delay(1000)
            swipeRefreshLayout.isRefreshing = false
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
                showHistoryDialog()
                true
            }
            R.id.action_share -> {
                shareZipFiles()
                true
            }
            else -> super.onOptionsItemSelected(item)
        }
    }
    
    private fun shareZipFiles() {
        val prefs = getSharedPreferences("app_prefs", Context.MODE_PRIVATE)
        val savedEmail = prefs.getString("share_email", "")
        
        val input = android.widget.EditText(this)
        input.hint = "接收邮箱 (选填)"
        input.setText(savedEmail)
        
        AlertDialog.Builder(this)
            .setTitle("分享新闻包")
            .setMessage("请输入接收邮箱（留空则手动选择分享应用）")
            .setView(input)
            .setPositiveButton("分享") { _, _ ->
                val email = input.text.toString().trim()
                if (email.isNotEmpty()) {
                    prefs.edit().putString("share_email", email).apply()
                }
                executeShare(email)
            }
            .setNegativeButton("取消", null)
            .show()
    }

    private fun executeShare(targetEmail: String) {
        lifecycleScope.launch(Dispatchers.IO) {
            // Correct path: /Android/data/pkg/files/PostGarden/data/
            val rootDir = getExternalFilesDir(null) ?: filesDir
            val dataDir = File(File(rootDir, "PostGarden"), "data")
            val versionFile = File(dataDir, "latest_versions.json")
            
            val zipFiles = ArrayList<File>()
            
            if (versionFile.exists()) {
                try {
                    val json = versionFile.readText()
                    // Simple parsing to avoid dependency on specific data class structure if it changes
                    // Or use the Repository's data class
                    val versions = com.google.gson.Gson().fromJson(json, com.example.postgarden.data.LatestVersions::class.java)
                    
                    if (versions != null) {
                        if (!versions.home.isNullOrEmpty()) zipFiles.add(File(dataDir, versions.home))
                        if (!versions.world.isNullOrEmpty()) zipFiles.add(File(dataDir, versions.world))
                        if (!versions.entertainment.isNullOrEmpty()) zipFiles.add(File(dataDir, versions.entertainment))
                    }
                } catch (e: Exception) {
                    e.printStackTrace()
                }
            } else {
                 // Fallback: If no version file, try latest by time
                 dataDir.listFiles { file -> 
                    file.extension == "zip" && 
                    (file.name.startsWith("Home_") || 
                     file.name.startsWith("World_") || 
                     file.name.startsWith("Entertainment_"))
                }?.sortedByDescending { it.lastModified() }?.take(3)?.let { zipFiles.addAll(it) }
            }
            
            // Filter out non-existent files
            val existingFiles = zipFiles.filter { it.exists() }

            if (existingFiles.isEmpty()) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@MainActivity, "没有可分享的文件 (目录: ${dataDir.name})", Toast.LENGTH_LONG).show()
                }
                return@launch
            }

            val uris = ArrayList<Uri>()
            for (file in existingFiles) {
                val uri = FileProvider.getUriForFile(
                    this@MainActivity,
                    "${packageName}.fileprovider",
                    file
                )
                uris.add(uri)
            }

            val shareIntent = Intent().apply {
                if (uris.size == 1) {
                    action = Intent.ACTION_SEND
                    putExtra(Intent.EXTRA_STREAM, uris[0])
                } else {
                    action = Intent.ACTION_SEND_MULTIPLE
                    putParcelableArrayListExtra(Intent.EXTRA_STREAM, uris)
                }
                type = "application/zip"
                if (targetEmail.isNotEmpty()) {
                    putExtra(Intent.EXTRA_EMAIL, arrayOf(targetEmail))
                    putExtra(Intent.EXTRA_SUBJECT, "PostGarden News Report")
                    putExtra(Intent.EXTRA_TEXT, "Here are the latest news reports from PostGarden.")
                }
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }

            withContext(Dispatchers.Main) {
                startActivity(Intent.createChooser(shareIntent, "发送给..."))
            }
        }
    }

    private fun showHistoryDialog() {
        val dialogView = layoutInflater.inflate(R.layout.dialog_history, null)
        val rvHistory = dialogView.findViewById<RecyclerView>(R.id.rvHistoryDialog)
        val btnClose = dialogView.findViewById<ImageButton>(R.id.btn_close_history)
        
        rvHistory.layoutManager = LinearLayoutManager(this)
        val historyRepo = ReadHistoryRepository(this)
        val historyItems = historyRepo.getHistory()
        
        val historyAdapter = HistoryAdapter { item ->
            if (item.url.isNotEmpty()) {
                val intent = Intent(this, WebViewActivity::class.java).apply {
                    putExtra("url", item.url)
                    putExtra("title", item.title)
                }
                startActivity(intent)
            }
        }
        
        rvHistory.adapter = historyAdapter
        historyAdapter.submitList(historyItems)
        
        val density = resources.displayMetrics.density
        val itemHeightPx = (60 * density).toInt() 
        val totalEstimatedHeight = historyItems.size * itemHeightPx
        val halfScreenHeight = resources.displayMetrics.heightPixels / 2
        
        if (totalEstimatedHeight > halfScreenHeight) {
            rvHistory.layoutParams.height = halfScreenHeight
        } else {
            rvHistory.layoutParams.height = ViewGroup.LayoutParams.WRAP_CONTENT
        }

        val dialog = AlertDialog.Builder(this)
            .setView(dialogView)
            .setCancelable(true) 
            .create()
            
        btnClose.setOnClickListener { dialog.dismiss() }
            
        dialog.show()
        dialog.setCanceledOnTouchOutside(true)
        
        val window = dialog.window
        window?.setBackgroundDrawable(ColorDrawable(Color.TRANSPARENT))
        val width = (resources.displayMetrics.widthPixels * 0.9).toInt()
        window?.setLayout(width, ViewGroup.LayoutParams.WRAP_CONTENT)
    }

    private fun displayReport(items: List<PolishedNewsItem>) {
        lifecycleScope.launch {
            // Update the favorites set in adapter for correct icon state
            val favs = favManager.getFavorites()
            val favUrls = favs.mapNotNull { it.sourceUrl }.toSet()
            
            newsAdapter.updateFavoriteSet(favUrls)
            
            if (items.isEmpty()) {
                newsAdapter.submitList(emptyList())
            } else {
                val newsItemsForDisplay = items.filter { it.rank > 0 }
                newsAdapter.submitList(newsItemsForDisplay) {
                    rvNews.scrollToPosition(0)
                }
            }
        }
    }
}