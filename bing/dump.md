Here's your Python script! 

## Key Features Implemented:

1. ✅ **Scrapes top 100 movies and shows** from IMDb chart pages
2. ✅ **PostgreSQL integration** with connection details from environment variables
3. ✅ **Duplicate checking** - queries existing IMDb IDs before inserting
4. ✅ **Batch commits** - commits every 10 entries
5. ✅ **SSL verification disabled** (`verify=False` in requests)
6. ✅ **Rate limiting** - 2 second delay between scraping pages
7. ✅ **Error handling** - continues on individual entry failures
8. ✅ **Progress tracking** - prints status throughout execution

## Environment Variables Needed:

Set these before running:
```bash
export DB_HOST="your_host"
export DB_NAME="your_database"
export DB_USER="your_username"
export DB_PASSWORD="your_password"
export DB_PORT="5432"
```

## Required Python Packages:

```bash
pip install requests beautifulsoup4 psycopg2-binary
```

## Usage:

```bash
python script_name.py
```

The script will:
- Scrape both pages
- Check for existing entries
- Insert only new ones
- Show a summary at the end

Let me know if you need any adjustments!