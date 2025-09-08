# Metadata Fetcher

A Python application that fetches comprehensive metadata for movies and TV shows from TMDB (The Movie Database) based on primary topic IDs stored in a PostgreSQL database.

## Features

- Fetches detailed metadata from TMDB API
- Supports both movies and TV shows
- Fallback search functionality when direct IDs are not available
- Comprehensive logging with optional file output
- Extensible architecture for future IMDB and UMD integration
- Error handling and graceful degradation

## Project Structure

```
project/
├── main.py                 # Entry point
├── config/
│   └── settings.py        # Environment configuration
├── database/
│   └── db_manager.py      # Database operations
├── services/
│   ├── tmdb_service.py    # TMDB API integration
│   ├── imdb_service.py    # Future IMDB implementation
│   └── umd_service.py     # Future UMD implementation
├── utils/
│   └── logger.py          # Logging configuration
├── logs/                  # Log files directory (created automatically)
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
└── README.md             # This file
```

## Setup Instructions

### 1. Prerequisites

- Python 3.7 or higher
- PostgreSQL database with `bingeplus_external` schema
- TMDB API Bearer Token

### 2. Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd metadata-fetcher
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

   **Note for Windows users:** If you encounter psycopg2 DLL errors:
   ```bash
   pip uninstall psycopg2-binary
   pip install psycopg2-binary --force-reinstall --no-cache-dir
   ```

3. **Create environment file**
   ```bash
   cp .env.example .env
   ```

4. **Configure environment variables**
   Edit the `.env` file with your actual values:
   ```env
   # Database Configuration
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=your_database
   DB_USER=your_username
   DB_PASSWORD=your_password

   # TMDB Configuration
   TMDB_BEARER_TOKEN=your_tmdb_bearer_token

   # Logging Configuration
   ENABLE_FILE_LOGGING=true
   LOG_LEVEL=INFO
   ```

### 3. Database Schema

The application expects the following tables in the `bingeplus_external` schema:

**primary_topics**
- `primary_topic_id` (Primary Key)
- `type` (movie, show, youtube_video)
- `name`
- `linked_umd_program_id`
- `description`
- `date`
- `is_block`

**topic_sources**
- `id` (Primary Key)
- `primary_topic_id` (Foreign Key)
- `source_id` (TMDB/IMDB IDs like tt799710)
- `source_name` (imdb, tmdb, umd, others)
- `source_id_type` (imdb_id, tmdb_id, umd_program_id, others)

## Usage

### Command Line

```bash
python main.py <primary_topic_id>
```

**Example:**
```bash
python main.py 420
```

### Programmatic Usage

```python
from main import fetch_metadata

# Fetch metadata for primary_topic_id = 420
result = fetch_metadata(420)
print(result)
```

## Response Schema

### Successful Response

```json
{
  "tmdb": {
    "title": "The Shawshank Redemption",
    "description": "Framed in the 1940s for the double murder of his wife and her lover...",
    "program_type": "movie",
    "cast": [
      {
        "castName": "Tim Robbins",
        "castRole": "actor"
      },
      {
        "castName": "Frank Darabont",
        "castRole": "director"
      }
    ],
    "releasedate": "1994-09-23",
    "genre": ["Drama", "Crime"],
    "tmdbRating": 8.7,
    "tmdbVoteCount": 26847,
    "plot": "Framed in the 1940s for the double murder...",
    "keywords": ["prison", "friendship", "hope"],
    "countryOrigin": "United States",
    "runtime": 142,
    "status": "Released",
    "originalLanguage": "en",
    "popularity": 89.456,
    "budget": 25000000,
    "revenue": 16000000,
    "tagline": "Fear can hold you prisoner. Hope can set you free.",
    "homepage": "",
    "posterPath": "/q6y0Go1tsGEsmtFryDOJo3dEmqu.jpg",
    "backdropPath": "/iNh3BivHyg5sQRPP1KOkzguEX0H.jpg",
    "adult": false,
    "tmdbId": 278,
    "imdbId": "tt0111161",
    "productionCompanies": ["Castle Rock Entertainment"],
    "spokenLanguages": ["English"],
    "numberOfSeasons": null,
    "numberOfEpisodes": null
  }
}
```

### Error Responses

**Content not found in database:**
```json
{
  "error": "Content not found in database",
  "primary_topic_id": 420
}
```

**Content not found in TMDB:**
```json
{
  "error": "Content not found in TMDB",
  "primary_topic_info": {
    "name": "Some Movie Name",
    "type": "movie"
  }
}
```

**Configuration error:**
```json
{
  "error": "Configuration error",
  "message": "Missing required environment variables: TMDB_BEARER_TOKEN"
}
```

## Data Flow

1. **Database Query**: Join `primary_topics` with `topic_sources` to get content info and available IDs
2. **ID Resolution**: 
   - Use TMDB ID directly if available
   - Convert IMDB ID to TMDB ID if only IMDB ID exists
   - Search by name and type if no IDs available
3. **API Calls**: Fetch data from multiple TMDB endpoints:
   - Basic info (`/movie/{id}` or `/tv/{id}`)
   - Credits (`/movie/{id}/credits`)
   - Keywords (`/movie/{id}/keywords`)
   - External IDs (`/movie/{id}/external_ids`)
4. **Response Building**: Combine all data into structured JSON response

## Logging

The application provides comprehensive logging:

- **Console Logging**: Always enabled
- **File Logging**: Optional (controlled by `ENABLE_FILE_LOGGING` environment variable)
- **Log Files**: Saved in `logs/` directory with timestamp: `metadata_fetcher_YYYYMMDD_HHMMSS.log`
- **Log Levels**: Configurable via `LOG_LEVEL` environment variable (DEBUG, INFO, WARNING, ERROR)

## Error Handling

- Database connection failures
- Missing environment variables
- TMDB API errors and rate limiting
- Content not found scenarios
- Invalid primary_topic_id values

## Future Extensions

The codebase is structured to easily add:

- **IMDB Service**: Direct IMDB data fetching
- **UMD Service**: Internal UMD program data integration
- **Additional Metadata Sources**: Any new metadata providers

## Troubleshooting

### Common Issues

1. **psycopg2 DLL Error (Windows)**
   ```bash
   pip install psycopg2-binary --force-reinstall --no-cache-dir
   ```

2. **Database Connection Failed**
   - Verify database credentials in `.env`
   - Ensure PostgreSQL is running
   - Check network connectivity

3. **TMDB API Errors**
   - Verify TMDB Bearer Token is valid
   - Check API rate limits
   - Ensure internet connectivity

4. **Missing Environment Variables**
   - Ensure `.env` file exists
   - Verify all required variables are set
   - Check for typos in variable names

### Debug Mode

Enable debug logging for detailed troubleshooting:
```env
LOG_LEVEL=DEBUG
ENABLE_FILE_LOGGING=true
```

## Contributing

When adding new metadata sources:

1. Create a new service class in `services/` directory
2. Implement the same interface as `TMDBService`
3. Add service integration in `main.py`
4. Update this README with new response schema fields

## License

[Add your license information here]