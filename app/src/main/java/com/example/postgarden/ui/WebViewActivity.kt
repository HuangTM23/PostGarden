package com.example.postgarden.ui

import android.os.Bundle
import android.view.View
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.ProgressBar
import androidx.appcompat.app.AppCompatActivity
import com.example.postgarden.R
import com.example.postgarden.data.ReadHistoryRepository
import com.google.android.material.appbar.MaterialToolbar

class WebViewActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_webview)

        val url = intent.getStringExtra("url") ?: ""
        val title = intent.getStringExtra("title") ?: "新闻详情"

        // Save to History
        if (url.isNotEmpty() && title.isNotEmpty()) {
            ReadHistoryRepository(this).addHistory(title, url)
        }

        val toolbar = findViewById<MaterialToolbar>(R.id.toolbar_webview)
        toolbar.title = title
        setSupportActionBar(toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        toolbar.setNavigationOnClickListener { finish() }

        val progressBar = findViewById<ProgressBar>(R.id.progressBar)
        val webView = findViewById<WebView>(R.id.webView)

        val settings = webView.settings
        settings.javaScriptEnabled = true
        settings.domStorageEnabled = true
        settings.useWideViewPort = true
        settings.loadWithOverviewMode = true
        
        // Default to Mobile UA
        var ua = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        
        // Use Desktop UA for Douyin and Bilibili to avoid forced app download prompts
        if (url.contains("douyin.com") || url.contains("bilibili.com")) {
            ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            settings.setSupportZoom(true)
            settings.builtInZoomControls = true
            settings.displayZoomControls = false
        }
        
        settings.userAgentString = ua
        
        // Video playback settings
        settings.mediaPlaybackRequiresUserGesture = false
        settings.mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW

        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView?, request: android.webkit.WebResourceRequest?): Boolean {
                val url = request?.url?.toString() ?: return false
                return handleUrl(view, url)
            }

            @Deprecated("Deprecated in Java")
            override fun shouldOverrideUrlLoading(view: WebView?, url: String?): Boolean {
                return handleUrl(view, url)
            }

            private fun handleUrl(view: WebView?, url: String?): Boolean {
                if (url == null) return false
                
                if (url.startsWith("http://") || url.startsWith("https://")) {
                    return false // Let WebView load it
                } else {
                    // Try to launch external app
                    try {
                        val intent = android.content.Intent(android.content.Intent.ACTION_VIEW, android.net.Uri.parse(url))
                        view?.context?.startActivity(intent)
                    } catch (e: Exception) {
                        // App not installed
                    }
                    return true // Block WebView from loading this URL
                }
            }
        }

        webView.webChromeClient = object : WebChromeClient() {
            private var customView: View? = null
            private var customViewCallback: CustomViewCallback? = null

            override fun onProgressChanged(view: WebView?, newProgress: Int) {
                if (newProgress == 100) {
                    progressBar.visibility = View.GONE
                } else {
                    progressBar.visibility = View.VISIBLE
                    progressBar.progress = newProgress
                }
            }
            
            override fun onShowCustomView(view: View?, callback: CustomViewCallback?) {
                super.onShowCustomView(view, callback)
                if (customView != null) {
                    callback?.onCustomViewHidden()
                    return
                }
                
                try {
                    customView = view
                    customViewCallback = callback
                    
                    toolbar.visibility = View.GONE
                    webView.visibility = View.GONE
                    
                    val decor = window.decorView as? android.view.ViewGroup
                    decor?.addView(customView, 
                        android.view.ViewGroup.LayoutParams(
                            android.view.ViewGroup.LayoutParams.MATCH_PARENT,
                            android.view.ViewGroup.LayoutParams.MATCH_PARENT
                        ))
                } catch (e: Exception) {
                    e.printStackTrace()
                    // Fallback: exit fullscreen
                    onHideCustomView()
                }
            }

            override fun onHideCustomView() {
                super.onHideCustomView()
                if (customView == null) return
                
                (window.decorView as android.widget.FrameLayout).removeView(customView)
                customView = null
                customViewCallback?.onCustomViewHidden()
                
                webView.visibility = View.VISIBLE
                toolbar.visibility = View.VISIBLE
            }
        }

        webView.loadUrl(url)
    }

    override fun onBackPressed() {
        val webView = findViewById<WebView>(R.id.webView)
        if (webView.canGoBack()) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }
}
