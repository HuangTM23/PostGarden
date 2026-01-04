# PostGarden App (Android)

This is the Android App V1 for PostGarden, designed to aggregate content from multiple platforms.
It currently implements the core crawling functionality cloned from the `NewsRank` and `worldnews` Python projects.

## Features
- **Multi-Platform Fetching**: Native Android implementation of content scrapers.
- **Baidu Hot Search**: Fetches real-time hot topics from Baidu (cloned from `NewsRank`).
- **BBC News**: Fetches "Most Read" articles from BBC (cloned from `worldnews`).
- **Tech Stack**: Kotlin, Coroutines, OkHttp, Jsoup.

## Project Structure
- `app/src/main/java/com/example/postgarden/data/`: Contains the Fetcher logic.
  - `BaiduHotFetcher.kt`: Implements Baidu API parsing.
  - `BBCFetcher.kt`: Implements BBC HTML parsing using Jsoup.
- `MainActivity.kt`: Simple UI to trigger fetches and display results.

## How to Run
1. Open this directory (`PostGarden`) in **Android Studio**.
2. Sync Gradle (The `build.gradle.kts` files are configured).
3. Run the `app` configuration on an Emulator or Device.
4. Click "Fetch Baidu Hot" or "Fetch BBC News" to see the results.

## Note on Python Scripts
The original Python scripts are located in `NewsRank/` and `worldnews/`. This Android app is a port of their logic to a native mobile environment, removing the dependency on external Python execution for the basic fetching tasks.
