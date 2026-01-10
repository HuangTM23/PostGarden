package com.example.postgarden.ui

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.postgarden.R
import com.example.postgarden.data.ReportRepository

class HistoryActivity : AppCompatActivity() {

    private lateinit var repository: ReportRepository
    private lateinit var adapter: HistoryAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_history)
        title = "Local Cache"

        repository = ReportRepository(this)
        
        val rvHistory = findViewById<RecyclerView>(R.id.rvHistory)
        rvHistory.layoutManager = LinearLayoutManager(this)
        
        adapter = HistoryAdapter { report ->
            val resultIntent = Intent()
            resultIntent.putExtra("selected_type", report.type)
            setResult(Activity.RESULT_OK, resultIntent)
            finish()
        }
        
        rvHistory.adapter = adapter
        
        loadHistory()
    }

    private fun loadHistory() {
        val reports = repository.getCachedReports()
        adapter.submitList(reports)
    }
}
