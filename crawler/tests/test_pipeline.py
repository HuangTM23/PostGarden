import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import shutil

# Add crawler directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pipeline

class TestPipeline(unittest.TestCase):

    def setUp(self):
        # Create a temp output dir for testing
        self.test_output_dir = "test_output"
        if os.path.exists(self.test_output_dir):
            shutil.rmtree(self.test_output_dir)
        os.makedirs(self.test_output_dir)
        
        # Patch configuration in pipeline
        self.original_output_dir = pipeline.OUTPUT_DIR
        pipeline.OUTPUT_DIR = self.test_output_dir
        pipeline.IMAGES_DIR = os.path.join(self.test_output_dir, "images")

    def tearDown(self):
        # Clean up
        if os.path.exists(self.test_output_dir):
            shutil.rmtree(self.test_output_dir)
        pipeline.OUTPUT_DIR = self.original_output_dir
        pipeline.IMAGES_DIR = os.path.join(self.original_output_dir, "images")

    @patch('pipeline.fetch_baidu.main')
    @patch('pipeline.fetch_toutiao.main')
    @patch('pipeline.fetch_tencent.main')
    @patch('pipeline.polish.main')
    @patch('pipeline.download_image')
    def test_run_pipeline_success(self, mock_download, mock_polish, mock_tencent, mock_toutiao, mock_baidu):
        # Mock fetchers
        mock_baidu.return_value = [{"title": "Baidu News", "rank": 1}]
        mock_toutiao.return_value = [{"title": "Toutiao News", "rank": 1}]
        mock_tencent.return_value = [{"title": "Tencent News", "rank": 1}]
        
        # Mock polish
        mock_polish.return_value = {
            "news": [
                {"rank": 0, "title": "Summary"},
                {"rank": 1, "title": "Polished News", "image": "http://example.com/img.jpg", "source_platform": "Baidu"}
            ]
        }
        
        # Mock download
        mock_download.return_value = True
        
        # Run pipeline
        pipeline.run_pipeline("morning")
        
        # Verify JSON file created
        json_path = os.path.join(self.test_output_dir, "morning.json")
        self.assertTrue(os.path.exists(json_path))
        
        # Verify ZIP file created
        zip_path = os.path.join(self.test_output_dir, "morning_report.zip")
        self.assertTrue(os.path.exists(zip_path))
        
    @patch('pipeline.fetch_baidu.main')
    @patch('pipeline.fetch_toutiao.main')
    @patch('pipeline.fetch_tencent.main')
    def test_run_pipeline_no_news(self, mock_tencent, mock_toutiao, mock_baidu):
        # Mock fetchers return empty
        mock_baidu.return_value = []
        mock_toutiao.return_value = []
        mock_tencent.return_value = []
        
        pipeline.run_pipeline("morning")
        
        # Verify NO JSON file created
        json_path = os.path.join(self.test_output_dir, "morning.json")
        self.assertFalse(os.path.exists(json_path))

if __name__ == '__main__':
    unittest.main()
