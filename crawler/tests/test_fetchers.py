import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json

# Add crawler directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import fetch_baidu
import fetch_toutiao
import fetch_tencent

class TestFetchers(unittest.TestCase):

    @patch('fetch_baidu.requests.get')
    def test_fetch_baidu(self, mock_get):
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "cards": [
                    {
                        "content": [
                            {
                                "word": "Test Title 1",
                                "desc": "Test Description 1",
                                "url": "http://baidu.com/1",
                                "img": "http://baidu.com/img1.jpg",
                                "hotScore": "1000"
                            }
                        ]
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        results = fetch_baidu.fetch_top_list(limit=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], "Test Title 1")
        self.assertEqual(results[0]['hot_score'], "1000")

    @patch('fetch_toutiao.requests.get')
    def test_fetch_toutiao(self, mock_get):
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "Title": "Toutiao Title 1",
                    "HotValue": "2000",
                    "Url": "http://toutiao.com/1",
                    "Image": {"url": "http://toutiao.com/img1.jpg"}
                }
            ]
        }
        mock_get.return_value = mock_response

        results = fetch_toutiao.main(limit=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], "Toutiao Title 1")
        self.assertEqual(results[0]['source_platform'], "Toutiao")

    @patch('fetch_tencent.get_links_auto')
    @patch('fetch_tencent.requests.get')
    @patch('fetch_tencent.download_image')
    @patch('os.makedirs')  # Prevent creating directories
    @patch('builtins.open') # Prevent writing files
    def test_fetch_tencent(self, mock_open, mock_makedirs, mock_download, mock_requests_get, mock_get_links):
        # Mock Selenium link fetching
        mock_get_links.return_value = ["http://news.qq.com/article1"]

        # Mock HTML response for article details
        mock_html_response = MagicMock()
        mock_html_response.status_code = 200
        mock_html_response.text = """
        <html>
            <head><title>Tencent Article Title</title></head>
            <body>
                <div class="content-article">
                    <p>This is a test paragraph for the article content.</p>
                </div>
                <span class="media-name">Tencent News</span>
            </body>
        </html>
        """
        mock_requests_get.return_value = mock_html_response

        # Mock image download
        mock_download.return_value = "mock_image_path.jpg"

        # Mock file writing for the final JSON dump
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        # Run main. We need to be careful as main() writes files.
        # We mocked open() so it shouldn't write to disk.
        # But main() doesn't return the data, it dumps it.
        # So we might want to test `get_article_details` directly first.
        
        config = {
             "id": "test_id",
             "name": "Test News",
             "json_prefix": "test_prefix",
             "img_dir": "test_images"
        }
        
        details = fetch_tencent.get_article_details("http://news.qq.com/article1", 1, config)
        
        self.assertIsNotNone(details)
        self.assertIn("Tencent Article Title", details['标题'])
        self.assertIn("This is a test paragraph", details['内容'])
        self.assertEqual(details['源平台'], "Tencent News")

    @patch('fetch_tencent.get_links_auto')
    @patch('fetch_tencent.get_article_details')
    @patch('os.makedirs')
    @patch('builtins.open')
    def test_fetch_tencent_main(self, mock_open, mock_makedirs, mock_details, mock_get_links):
        mock_get_links.return_value = ["http://news.qq.com/1"]
        mock_details.return_value = {
            "序号": 1,
            "标题": "Test Title",
            "内容": "Test Content",
            "源平台": "Tencent News",
            "源平台的链接": "http://news.qq.com/1",
            "封面图片": "test.jpg"
        }
        
        results = fetch_tencent.main(report_type="morning", limit=1)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], "Test Title")
        self.assertEqual(results[0]['source_platform'], "Tencent")


if __name__ == '__main__':
    unittest.main()
