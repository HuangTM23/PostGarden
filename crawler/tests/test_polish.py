import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json

# Add crawler directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import polish

class TestPolish(unittest.TestCase):

    @patch('polish.os.getenv')
    def test_no_api_key(self, mock_getenv):
        # Setup mock to return empty string for API KEY
        # We need to reload the module or patch the constant directly?
        # Since polish.DEEPSEEK_API_KEY is read at module level, patching getenv after import might be too late
        # unless we reload. Or we can patch polish.DEEPSEEK_API_KEY directly.
        with patch('polish.DEEPSEEK_API_KEY', ""):
            result = polish.main([])
            self.assertIsNone(result)

    @patch('polish.requests.post')
    def test_successful_polish(self, mock_post):
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_content = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({
                            "news": [
                                {"rank": 0, "title": "Summary"},
                                {"rank": 1, "title": "News 1"}
                            ]
                        })
                    }
                }
            ]
        }
        mock_response.json.return_value = mock_content
        mock_post.return_value = mock_response

        # Input data
        input_items = [
            {"title": "Raw 1", "content": "Content 1", "source_platform": "Baidu"}
        ]

        with patch('polish.DEEPSEEK_API_KEY', "test_key"):
            result = polish.main(input_items)
            
        self.assertIsNotNone(result)
        self.assertIn("news", result)
        self.assertEqual(len(result["news"]), 2)
        self.assertEqual(result["news"][0]["title"], "Summary")

    @patch('polish.requests.post')
    def test_api_failure_retry(self, mock_post):
        # Mock API to raise exception
        mock_post.side_effect = Exception("API Error")
        
        with patch('polish.DEEPSEEK_API_KEY', "test_key"):
            result = polish.main([], max_retries=2)
            
        self.assertIsNone(result)
        self.assertEqual(mock_post.call_count, 2)

    @patch('polish.requests.post')
    def test_invalid_json_response(self, mock_post):
        # Mock API to return valid JSON but wrong schema
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_content = {
            "choices": [
                {
                    "message": {
                        "content": "Not a JSON string" # This will cause json.loads to fail
                    }
                }
            ]
        }
        mock_response.json.return_value = mock_content
        mock_post.return_value = mock_response
        
        with patch('polish.DEEPSEEK_API_KEY', "test_key"):
            result = polish.main([], max_retries=1)
            
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
