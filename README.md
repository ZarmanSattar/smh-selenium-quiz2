# SMH News Scraper API

**Student:** FA23-BAI-053  
**Course:** CSC413 – DevOps for Cloud Computing  
**News Source:** Sydney Morning Herald (smh.com.au)

## Overview
A Dockerized Selenium automation system that searches the Sydney Morning Herald for a given keyword, fetches the first result, summarizes the article, and exposes the result via a REST API.

## Tech Stack
- Python + Flask (REST API)
- Selenium + Google Chrome (headless scraping)
- BeautifulSoup (article parsing)
- Docker

## API

**Endpoint:** `GET /get?keyword={keyword}`  
**Port:** `7000`

**Response:**
```json
{
  "registration": "FA23-BAI-053",
  "newssource": "Sydney Morning Herald",
  "keyword": "climate",
  "url": "https://www.smh.com.au/...",
  "summary": "..."
}
```

## Run Locally

```bash
docker pull zarman53/smh-selenium:v1
docker run -d -p 7000:7000 zarman53/smh-selenium:v1
curl "http://localhost:7000/get?keyword=climate"
```

## Build & Push

```bash
docker build -t zarman53/smh-selenium:v1 .
docker push zarman53/smh-selenium:v1
```
