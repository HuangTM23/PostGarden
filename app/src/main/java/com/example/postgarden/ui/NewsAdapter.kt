package com.example.postgarden.ui

import android.content.Intent
import android.net.Uri
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
import com.example.postgarden.data.PolishedNewsItem
import com.example.postgarden.R

class NewsAdapter(
    private val onFavoriteClick: (PolishedNewsItem) -> Unit,
    private val isFavoriteCheck: (PolishedNewsItem) -> Boolean
) : ListAdapter<PolishedNewsItem, NewsAdapter.NewsViewHolder>(NewsDiffCallback()) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): NewsViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_news, parent, false)
        return NewsViewHolder(view, onFavoriteClick, isFavoriteCheck)
    }

    override fun onBindViewHolder(holder: NewsViewHolder, position: Int) {
        val item = getItem(position)
        holder.bind(item)
    }

    class NewsViewHolder(
        itemView: View,
        private val onFavoriteClick: (PolishedNewsItem) -> Unit,
        private val isFavoriteCheck: (PolishedNewsItem) -> Boolean
    ) : RecyclerView.ViewHolder(itemView) {
        private val rankView: TextView = itemView.findViewById(R.id.tv_rank)
        private val titleView: TextView = itemView.findViewById(R.id.tv_title)
        private val contentView: TextView = itemView.findViewById(R.id.tv_content)
        private val sourceView: TextView = itemView.findViewById(R.id.tv_source)
        private val imageView: ImageView = itemView.findViewById(R.id.iv_news_image)
        private val favoriteBtn: ImageButton = itemView.findViewById(R.id.btn_favorite)

        fun bind(item: PolishedNewsItem) {
            rankView.text = "${item.rank}."
            titleView.text = item.title
            contentView.text = item.content
            sourceView.text = "来源: ${item.sourcePlatform}"
            
            // Open in browser on click
            itemView.setOnClickListener {
                if (item.sourceUrl.isNotEmpty()) {
                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(item.sourceUrl))
                    itemView.context.startActivity(intent)
                }
            }

            // Handle favorite click
            val isFav = isFavoriteCheck(item)
            favoriteBtn.setImageResource(
                if (isFav) R.drawable.ic_favorite_filled else R.drawable.ic_favorite_border
            )
            
            favoriteBtn.setOnClickListener {
                onFavoriteClick(item)
                // Re-bind to update icon instantly
                val nowFav = isFavoriteCheck(item)
                favoriteBtn.setImageResource(
                    if (nowFav) R.drawable.ic_favorite_filled else R.drawable.ic_favorite_border
                )
            }

            // Only load image if path is valid
            if (item.imagePath.isNotEmpty()) {
                Glide.with(itemView.context)
                    .load(item.fullImageUrl)
                    .centerCrop()
                    .placeholder(android.R.drawable.ic_menu_gallery)
                    .error(android.R.drawable.ic_menu_report_image)
                    .into(imageView)
            } else {
                imageView.setImageResource(android.R.drawable.ic_menu_gallery)
            }
        }
    }
}

class NewsDiffCallback : DiffUtil.ItemCallback<PolishedNewsItem>() {
    override fun areItemsTheSame(oldItem: PolishedNewsItem, newItem: PolishedNewsItem): Boolean {
        return oldItem.rank == newItem.rank && oldItem.sourceUrl == newItem.sourceUrl
    }

    override fun areContentsTheSame(oldItem: PolishedNewsItem, newItem: PolishedNewsItem): Boolean {
        return oldItem == newItem
    }
}
