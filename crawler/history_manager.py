import os
import json
from datetime import datetime, timedelta
import difflib

class HistoryManager:
    def __init__(self, history_file="output/news_history_7days.json", days_to_keep=7):
        self.history_file = history_file
        self.days_to_keep = days_to_keep
        self.history = self._load_history()

    def _load_history(self):
        if not os.path.exists(self.history_file):
            return []
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading history: {e}")
            return []

    def clean_old_history(self):
        """Removes entries older than days_to_keep."""
        cutoff_date = datetime.now() - timedelta(days=self.days_to_keep)
        original_count = len(self.history)
        
        # Keep items where date is >= cutoff or date format is invalid (safety)
        new_history = []
        for item in self.history:
            try:
                item_date = datetime.strptime(item.get('date', ''), "%Y-%m-%d")
                if item_date >= cutoff_date:
                    new_history.append(item)
            except ValueError:
                # If date format is wrong, maybe keep it or drop it? Let's drop to self-heal.
                pass
        
        self.history = new_history
        if len(self.history) < original_count:
            print(f"  [History] Cleaned {original_count - len(self.history)} old items.")
            self._save_history()

    def _save_history(self):
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")

    def is_duplicate(self, title, content, threshold=0.7):
        """
        Check if the news is duplicate based on title or content similarity.
        Threshold: 0.7 means 70% similarity.
        """
        if not title: return False
        
        for item in self.history:
            hist_title = item.get('title', '')
            hist_content = item.get('content', '')

            # 1. Direct Title Match (Fast)
            if title == hist_title:
                return True

            # 2. Title Similarity
            # Use SequenceMatcher for similarity
            if difflib.SequenceMatcher(None, title, hist_title).ratio() > threshold:
                return True
                
            # 3. Content Similarity (Only if content is substantial)
            if content and hist_content and len(content) > 50 and len(hist_content) > 50:
                if difflib.SequenceMatcher(None, content[:200], hist_content[:200]).ratio() > threshold:
                    return True
        
        return False

    def add_news(self, news_list, category="unknown"):
        """
        Adds a list of polished news items to history.
        Expected format: list of dicts with 'title' and 'content' keys.
        """
        today_str = datetime.now().strftime("%Y-%m-%d")
        count = 0
        for item in news_list:
            title = item.get('title')
            if not title: continue
            
            # Avoid adding duplicates within the same batch if possible, 
            # though usually news_list is already polished.
            
            entry = {
                "title": title,
                "content": item.get('content', ''),
                "date": today_str,
                "category": category
            }
            self.history.append(entry)
            count += 1
            
        if count > 0:
            self._save_history()
            print(f"  [History] Added {count} items to history.")

