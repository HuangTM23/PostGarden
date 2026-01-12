package com.example.postgarden

import android.app.AlertDialog
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.drawable.ColorDrawable
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
import com.google.android.material.floatingactionbutton.FloatingActionButton
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : AppCompatActivity() {

    private lateinit var rvNews: RecyclerView
    private lateinit var newsAdapter: NewsAdapter
    private val apiClient = ApiClient()
    private lateinit var repository: ReportRepository
    private lateinit var favManager: FavoritesManager // New Manager
    private lateinit var toolbar: MaterialToolbar
    private lateinit var bottomNavigationView: BottomNavigationView
    
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
        val fabRefresh = findViewById<FloatingActionButton>(R.id.fabRefresh)
        bottomNavigationView = findViewById(R.id.bottomNavigationView)
        
        repository = ReportRepository(this)
        favManager = FavoritesManager(this) // Initialize new manager

        newsAdapter = NewsAdapter(
            onFavoriteClick = { item ->
                handleFavoriteClick(item)
            },
            // This checker needs to be synchronous for bind(), so we might need a synchronous way 
            // OR the adapter should not rely on a callback for binding state if it's expensive.
            // But checking memory cache in FavManager is fast and now thread-safe.
            // However, runBlocking on UI thread is bad. 
            // Better approach: Adapter holds a Set of favorite IDs.
            isFavoriteCheck = { false } // Placeholder, will update logic below
        )

        rvNews.layoutManager = LinearLayoutManager(this)
        rvNews.adapter = newsAdapter

        fabRefresh.setOnClickListener {
            if (!isRefreshing) {
                manualRefresh()
            }
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
        
        // 2. Start Background Update
        startBackgroundUpdate()
        
        // 3. Pre-load favorites into memory
        lifecycleScope.launch { favManager.getFavorites() }
    }

    private fun handleFavoriteClick(item: PolishedNewsItem) {
        lifecycleScope.launch {
            try {
                val isFav = favManager.isFavorite(item.sourceUrl)
                if (isFav) {
                    favManager.removeFavorite(item)
                    Toast.makeText(this@MainActivity, "已取消收藏", Toast.LENGTH_SHORT).show()
                    // If we are currently viewing favorites, refresh the list
                    if (bottomNavigationView.selectedItemId == R.id.nav_favorites) {
                        loadFavorites()
                    }
                } else {
                    favManager.addFavorite(item)
                    Toast.makeText(this@MainActivity, "已加入收藏", Toast.LENGTH_SHORT).show()
                }
                
                // Notify adapter to update this specific item's appearance
                // Since we don't have the position easily here, we might need to rely on 
                // notifying dataset changed or finding the item.
                // For simplicity/robustness, let's just refresh the visible list's state binding.
                newsAdapter.notifyDataSetChanged()
                
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
        }
    }

    private fun loadLocalData(): Boolean {
        // If we are on favorites tab, don't load regular report
        if (bottomNavigationView.selectedItemId == R.id.nav_favorites) {
            loadFavorites()
            return true
        }
        
        val report = repository.getLocalReport(currentReportType)
        if (report.news.isNotEmpty()) {
            displayReport(report.news)
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
                    withContext(Dispatchers.Main) { progressBar.visibility = View.GONE }
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
                            // Only refresh if not viewing favorites
                            if (bottomNavigationView.selectedItemId != R.id.nav_favorites) {
                                loadLocalData()
                            }
                        }
                    }
                }
                withContext(Dispatchers.Main) { progressBar.visibility = View.GONE }
            } catch (e: Exception) {
                e.printStackTrace()
                withContext(Dispatchers.Main) { progressBar.visibility = View.GONE }
            }
        }
    }
    
    private fun manualRefresh() {
        // If on favorites, just reload favorites
        if (bottomNavigationView.selectedItemId == R.id.nav_favorites) {
            loadFavorites()
            return
        }
        
        val fabRefresh = findViewById<FloatingActionButton>(R.id.fabRefresh)
        isRefreshing = true
        fabRefresh.isEnabled = false 
        fabRefresh.setImageResource(R.drawable.ic_refresh)
        progressBar.visibility = View.VISIBLE
        
        lifecycleScope.launch {
            startBackgroundUpdate()
            delay(1500)
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
                showHistoryDialog()
                true
            }
            else -> super.onOptionsItemSelected(item)
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
        
        // Dynamic Height Logic
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
        // Need to update adapter with a way to check favorites synchronously or async
        // We will pass a set of favorite URLs to the adapter
        lifecycleScope.launch {
            // Get all favorite URLs for quick checking
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