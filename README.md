# Scrapy Frontier Crawler

A configurable web crawler built with Scrapy and Playwright for handling both static and dynamic content. The crawler can process different types of URLs and store results in a PostgreSQL database.

## Features

- 🔍 Three types of URL processing:
  - Type 0: Direct target URL processing
  - Type 1: Static page scanning for target URLs
  - Type 2: Dynamic page scanning with depth navigation
- 🎭 Playwright integration for JavaScript-rendered content
- 📊 PostgreSQL storage for crawled URLs and stats 
- 🔧 YAML-based configuration
- 📝 Structured logging with Logfire
- 🐳 Docker support
- ☁️ Azure deployment ready with Terraform

## Prerequisites

- Python 3.11+
- PostgreSQL database
- [uv](https://github.com/astral-sh/uv) for package management
- Docker (optional)


## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

