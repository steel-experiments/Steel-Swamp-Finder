# Property Finder

A Steel-powered web automation agent that searches any website for properties/listings, with full Raindrop monitoring for observability.

## What It Does

Searches any property listing website and extracts:
- Property/Listing Name
- Location (City/Region)
- Price and Currency
- Rating (out of 5)
- URL to listing
- Match Score (based on your keywords)

Results are ranked by match score and saved to `results.json`.

## Why This Demo?

This showcases realistic web automation challenges:

### Real-World Complexity
- **Any Website**: Works with Airbnb, njuskalo.hr, Booking.com, and similar listing sites
- **Dynamic Content**: Handles JavaScript rendering via Steel
- **Anti-Bot Detection**: Steel handles protection from major sites
- **Intelligent Extraction**: Works across different site structures

### Monitoring Points
Every action is logged to Raindrop:
- Browser initialization timing
- Page load performance
- Listing extraction success/failure
- Data validation
- File save operations

### Signals for Alerts
- `task_success` / `task_failure` - Overall outcome
- `results_found` - Found results
- `no_results` - Empty search
- `slow_scrape` - Performance issues (>8s)
- `scrape_failure` - Scraping problems
- `thin_content` - Low content warning

## Setup

### 1. Install Dependencies

```bash
pip install steel-browser raindrop-ai raindrop-query python-dotenv openai
```

### 2. Get API Keys

**Steel**: https://steel.dev
Free tier: 100 browser hours/month

**Raindrop**: https://app.raindrop.ai
Sign up and get your API keys

### 3. Configure Environment

Create `.env` file:

```bash
STEEL_API_KEY=ste_your_steel_key
RAINDROP_WRITE_KEY=your_raindrop_write_key
RAINDROP_QUERY_API_KEY=your_raindrop_query_key
OPENAI_API_KEY=sk_your_openai_key
```

**Note**: Raindrop uses separate keys for writing (`RAINDROP_WRITE_KEY`) and querying (`RAINDROP_QUERY_API_KEY`). Get both from https://app.raindrop.ai

### 4. Run It!

```bash
python PropertyFinder.py --url "https://www.airbnb.com/s/Porec--Croatia/homes" --prompt "apartments in Porec for vacation rental"
```

## Usage

### Basic Scraping

```bash
python PropertyFinder.py --url <url> --prompt "<what you're looking for>"

# Required Arguments:
#   --url       URL to scrape (any property listing site)
#   --prompt    Natural language description of what to find

# Optional Arguments:
#   --location    Location parameter for URL templates
#   --keywords    Scoring keywords, comma-separated (default: extracted from prompt)
```

### Examples

```bash
# Airbnb search
python PropertyFinder.py --url "https://www.airbnb.com/s/Porec--Croatia/homes" --prompt "apartments in Porec Istria"

# Croatian real estate (njuskalo.hr)
python PropertyFinder.py --url "https://www.njuskalo.hr/prodaja-stanova/split" --prompt "flats between 80 and 100 square meters"

# With custom keywords for better scoring
python PropertyFinder.py --url "https://www.njuskalo.hr/prodaja-kuca/zagreb" --prompt "houses with gardens" --keywords "garden,backyard,outdoor"

# URL templates with placeholders
python PropertyFinder.py --url "https://www.airbnb.com/s/{location}/homes" --location "Colorado" --prompt "secluded mountain cabin"
```

### Semantic Search Mode

Search your past runs using natural language:

```bash
# Search past runs by meaning
python PropertyFinder.py --query "colorado cabin finds"

# Find similar discoveries
python PropertyFinder.py --similar "secluded waterfront property"

# Find sessions with issues
python PropertyFinder.py --issues
```

## Example Output

```
PROPERTY FINDER
=====================================================================
URL      : https://www.airbnb.com/s/Porec--Croatia/homes
Prompt   : apartments in Porec Istria Croatia
Keywords : ['porec', 'istria', 'croatia']
Session  : search_20260219_135720
=====================================================================

Steel session: 247f7e14-d470-4aae-b2b4-67f6668b2646
Watch live: https://app.steel.dev/sessions/247f7e14-d470-4aae-b2b4-67f6668b2646
Scraping: https://www.airbnb.com/s/Porec--Croatia/homes...
Scraped 1351946 chars in 5.58s
Saved to results.json

=====================================================================
RESULTS - Ranked by Match Score
=====================================================================

1. Charming Cozy Stay for Two in Poreč
   Location: Poreč
   Price: $286   Match Score: 5.0/10
   Rating: 5.0/5.0
   URL: /rooms/1377529800182448220

2. Apartment Anka Studio
   Location: Poreč
   Price: $306   Match Score: 5.0/10
   Rating: 4.78/5.0
   URL: /rooms/24710726

3. Room with bathroom 2min from beach-10min from city
   Location: Poreč
   Price: $245   Match Score: 5.0/10
   Rating: 4.84/5.0
   URL: /rooms/12921386

=====================================================================
Top result: Charming Cozy Stay for Two in Poreč
   Poreč
=====================================================================

Done! Found 11 results.
See results.json for full data.
```

## Output File

Results are saved to `results.json`:

```json
{
  "session_id": "search_20260219_135720",
  "search_date": "2026-02-19T13:57:20",
  "total": 11,
  "keywords": ["porec", "istria", "croatia"],
  "results": [
    {
      "name": "Charming Cozy Stay for Two in Poreč",
      "location": "Poreč",
      "price_per_night": 286,
      "currency": "USD",
      "rating": 5.0,
      "url": "/rooms/1377529800182448220",
      "match_score": 5.0
    }
  ]
}
```

## Expected Results by Site

| Site | Expected Listings | Notes |
|------|-------------------|-------|
| njuskalo.hr | 10-15 | Croatian real estate, good extraction |
| airbnb.com | 10-11 | Vacation rentals with prices and ratings |
| booking.com | 2-3 | Heavy JS rendering, limited results |
| idealista.com | 0 | Anti-bot protection |

## Raindrop Monitoring Dashboard

### Event Timeline

```
[10:30:01] session_started (steel_session_id: abc123)
[10:30:01] page_scrape (url: https://www.airbnb.com/s/...)
[10:30:03] ai_extraction (count: 11)
[10:30:04] parse_listings (valid_count: 11)
[10:30:04] results_found (count: 11)
[10:30:04] results_saved (filename: results.json)
[10:30:04] session_released
[10:30:04] property_finder_run (results_found: 11)
```

### Signal Alerts

```
results_found (count: 11)
task_success (results_found: 11)
```

### Queries You Can Run in Raindrop

- `event:page_scrape` - See all scrape operations
- `signal:slow_scrape` - Find performance issues
- `results_found > 0` - Successful searches
- `duration_seconds > 10` - Slow executions
- `session_id:search_20260219_135720` - View specific run

## Match Scoring

Each property gets a "match score" (0-10) based on:
- Keyword matches in name, location, and description
- Price (cheaper = higher score)

Keywords come from:
- `--keywords` argument if provided
- Otherwise, automatically extracted from your `--prompt`

## Monitoring Benefits

### Without Raindrop
- Agent fails silently
- Don't know which step broke
- No performance tracking
- Hard to debug

### With Raindrop
- See exact failure point
- Full execution timeline
- Performance metrics
- Search by natural language
- Alert on anomalies
- Compare runs

## Troubleshooting

### No results found
- Try different prompt wording
- Check if the URL is correct
- Use `--issues` to find problematic sessions
- Watch the Steel session URL to see what's happening

### Fewer results than expected
- Some sites have anti-bot protection
- Check Raindrop traces with `--query "extraction listings"`
- Look at `raw_count` vs `valid_count` in traces

### Slow page loads
- Check Raindrop for `slow_scrape` signals
- Some sites can be slow with images loading
- Steel handles this automatically with timeouts

### Browser won't start
- Verify your Steel API key is correct
- Check you have browser hours remaining
- Look for `session_started` event in Raindrop

## Resources

- [Steel Documentation](https://docs.steel.dev)
- [Raindrop Documentation](https://docs.raindrop.ai)
- [Agent Skill Documentation](.agents/skills/propertyfinder/SKILL.md)
