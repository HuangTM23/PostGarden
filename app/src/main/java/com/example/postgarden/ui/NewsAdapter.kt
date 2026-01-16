package com.example.postgarden.ui

import android.content.Intent
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageButton
import android.widget.ImageView
import android.widget.TextView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.bumptech.glide.Glide
import com.example.postgarden.R
import com.example.postgarden.data.PolishedNewsItem

class NewsAdapter(
    private val onFavoriteClick: (PolishedNewsItem) -> Unit,
    private val isFavoriteCheck: (PolishedNewsItem) -> Boolean
) : ListAdapter<PolishedNewsItem, NewsAdapter.NewsViewHolder>(NewsDiffCallback()) {

    private var favoriteUrls: Set<String> = emptySet()

    fun updateFavoriteSet(newSet: Set<String>) {
        favoriteUrls = newSet
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): NewsViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_news, parent, false)
        return NewsViewHolder(view, onFavoriteClick)
    }

    override fun onBindViewHolder(holder: NewsViewHolder, position: Int) {
        val item = getItem(position)
        val isFav = favoriteUrls.contains(item.sourceUrl)
        holder.bind(item, isFav)
    }

    class NewsViewHolder(
        itemView: View,
        private val onFavoriteClick: (PolishedNewsItem) -> Unit
    ) : RecyclerView.ViewHolder(itemView) {
        private val originalTitleView: TextView = itemView.findViewById(R.id.tv_original_title)
        private val titleView: TextView = itemView.findViewById(R.id.tv_title)
        private val contentView: TextView = itemView.findViewById(R.id.tv_content)
        private val sourceView: TextView = itemView.findViewById(R.id.tv_source)
        private val imageView: ImageView = itemView.findViewById(R.id.iv_news_image)
        private val playIcon: ImageView = itemView.findViewById(R.id.iv_play_icon)
        private val favoriteBtn: ImageButton = itemView.findViewById(R.id.btn_favorite)

        fun bind(item: PolishedNewsItem, isFavorite: Boolean) {
            val isForeign = !item.originalTitle.isNullOrEmpty()

            // 1. Titles
            if (isForeign) {
                originalTitleView.text = item.originalTitle
                originalTitleView.visibility = View.VISIBLE
                titleView.text = item.title
                titleView.visibility = View.VISIBLE
            } else {
                originalTitleView.visibility = View.GONE
                titleView.text = item.title
                titleView.visibility = View.VISIBLE
            }
            
            // 2. Content (Summary pre-fetched in Repository)
            if (isForeign) {
                contentView.visibility = View.VISIBLE
                if (!item.summary.isNullOrEmpty()) {
                    contentView.text = item.summary
                } else {
                    contentView.text = "Summary loading failed or not available."
                }
            } else {
                contentView.visibility = View.GONE
            }

            sourceView.text = "Source: ${item.sourcePlatform}"
            val isVideoPlatform = item.sourcePlatform == "抖音" || item.sourcePlatform == "哔哩哔哩"
            playIcon.visibility = if (isVideoPlatform) View.VISIBLE else View.GONE
            
            itemView.setOnClickListener {
                if (!item.sourceUrl.isNullOrEmpty()) {
                    val intent = Intent(itemView.context, WebViewActivity::class.java).apply {
                        putExtra("url", item.sourceUrl)
                        putExtra("title", item.title ?: "")
                    }
                    itemView.context.startActivity(intent)
                }
            }

            updateFavoriteIcon(isFavorite)
            favoriteBtn.setOnClickListener {
                onFavoriteClick(item)
            }

            if (!item.imagePath.isNullOrEmpty()) {
                Glide.with(itemView.context)
                    .load(item.fullImageUrl)
                    .fitCenter() 
                    .placeholder(android.R.drawable.ic_menu_gallery)
                    .error(android.R.drawable.ic_menu_report_image)
                    .into(imageView)
            } else {
                imageView.setImageResource(android.R.drawable.ic_menu_gallery)
            }
        }

        private fun updateFavoriteIcon(isFavorite: Boolean) {
             favoriteBtn.setImageResource(
                if (isFavorite) R.drawable.ic_favorite_filled else R.drawable.ic_favorite_border
            )
        }
    }
}

class NewsDiffCallback : DiffUtil.ItemCallback<PolishedNewsItem>() {
    override fun areItemsTheSame(oldItem: PolishedNewsItem, newItem: PolishedNewsItem): Boolean {
        return oldItem.rank == newItem.rank && oldItem.sourceUrl == newItem.sourceUrl
    }

    override fun areContentsTheSame(oldItem: PolishedNewsItem, newItem: PolishedNewsItem): Boolean {
        // Since summary might change, we check it too
        return oldItem.title == newItem.title && 
               oldItem.summary == newItem.summary && 
               oldItem.originalTitle == newItem.originalTitle
    }
}
