# Property Finder

A Steel-powered web automation agent that searches any website for properties/listings, with full Raindrop monitoring for observability.

## What It Does

Searches any website using a URL template and extracts:
- Property/Listing Name
- Location (City/Region)
- Price per Night
- Rating (out of 5)
- Match Score (based on your keywords)

Results are ranked by match score and saved to `results.json`.

## Why This Demo?

This showcases realistic web automation challenges:

### Real-World Complexity
- **Flexible URL Templates**: Works with any website using `{query}` and `{location}` placeholders
- **Dynamic Content**: Handles JavaScript rendering via Steel
- **Anti-Bot Detection**: Steel handles protection from major sites
- **Complex DOM**: Real-world HTML structure parsing with fallbacks

### Monitoring Points
Every action is logged to Raindrop:
- Browser initialization timing
- Page load performance
- Search query execution
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
pip install steel-browser raindrop-ai raindrop-query python-dotenv
```

### 2. Get API Keys

**Steel**: https://steel.dev
Free tier: 100 browser hours/month

**Raindrop**: https://app.raindrop.ai
Sign up and get your API key

### 3. Configure Environment

Create `.env` file:

```bash
STEEL_API_KEY=sk_live_your_steel_key
RAINDROP_WRITE_KEY=your_raindrop_write_key
RAINDROP_QUERY_API_KEY=your_raindrop_query_key
```

**Note**: Raindrop uses separate keys for writing (`RAINDROP_WRITE_KEY`) and querying (`RAINDROP_QUERY_API_KEY`). Get both from https://app.raindrop.ai

### 4. Run It!

```bash
python PropertyFinder.py --url "https://www.airbnb.com/s/{location}/homes?query={query}" --location "Colorado" --query "cabin"
```

## Usage

### Basic Scraping

```bash
# Search with URL template
python PropertyFinder.py --url <url_template> --query <search_term> [options]

# Required Arguments:
#   --url      URL template with {query} and {location} placeholders
#   --query    Search term

# Optional Arguments:
#   --location    Location filter
#   --keywords    Scoring keywords, comma-separated (default: use query terms)
```

### URL Template Examples

```bash
# Airbnb search
python PropertyFinder.py --url "https://www.airbnb.com/s/{location}/homes?query={query}" --location "Colorado" --query "cabin"

# Generic search site
python PropertyFinder.py --url "https://example.com/search?q={query}" --query "beach house"

# With custom keywords for scoring
python PropertyFinder.py --url "https://site.com/listings?term={query}" --query "cabin" --keywords "cabin,secluded,rustic,nature"
```

### Semantic Query Search

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
URL      : https://www.airbnb.com/s/Colorado/homes?query=cabin
Query    : cabin
Keywords : ['cabin']
Session  : search_20260219_143022
=====================================================================

Steel session: abc123
Watch live: https://steel.dev/session/abc123
Scraping: https://www.airbnb.com/s/Colorado/homes?query=cabin...
Scraped 145832 chars in 2.34s
Saved to results.json
Session released

=====================================================================
RESULTS - Ranked by Match Score
=====================================================================

1. Secluded Mountain Cabin
   Location: Vail, Colorado
   $89/night   Rating: 4.87/5.0   Match Score: 9.5/10

2. Rustic Alpine Retreat
   Location: Breckenridge, Colorado
   $95/night   Rating: 4.68/5.0   Match Score: 9.2/10

3. Cozy Ski-In Cabin
   Location: Aspen, Colorado
   $110/night   Rating: 4.75/5.0   Match Score: 8.9/10

=====================================================================
Top result: Secluded Mountain Cabin
   Vail, Colorado
=====================================================================

Raindrop session: search_20260219_143022
```

## Raindrop Monitoring Dashboard

### Event Timeline

```
[10:30:01] session_started (steel_session_id: abc123)
[10:30:01] page_scrape (url: https://www.airbnb.com/s/...)
[10:30:03] parse_listings (content_length: 145832)
[10:30:04] json_parse_success (count: 5)
[10:30:04] results_found (count: 5)
[10:30:04] results_saved (filename: results.json)
[10:30:04] session_released
[10:30:04] property_finder_run (results_found: 5)
```

### Signal Alerts

```
results_found (count: 5)
task_success (results_found: 5)
```

### Queries You Can Run in Raindrop

- `event:page_scrape` - See all scrape operations
- `signal:slow_scrape` - Find performance issues
- `results_found > 0` - Successful searches
- `duration_seconds > 10` - Slow executions
- `session_id:search_20260219_143022` - View specific run

## Output File

Results are saved to `results.json`:

```json
{
  "session_id": "search_20260219_143022",
  "search_date": "2026-02-19T14:30:07",
  "total": 3,
  "keywords": ["cabin"],
  "results": [
    {
      "name": "Secluded Mountain Cabin",
      "location": "Vail, Colorado",
      "price_per_night": 89,
      "rating": 4.87,
      "match_score": 9.5
    }
  ]
}
```

## Important Notes

### Real Scraping Challenges

**Website DOMs change frequently**, so selectors may need updates. The agent handles this by:

1. **Trying JSON-LD first** - Structured data extraction
2. **Fallback to regex parsing** - Can extract data even if structured parsing fails
3. **Comprehensive logging** - Raindrop tracks which methods work/fail
4. **Graceful degradation** - Returns what it can find rather than crashing

**Anti-bot protection**: Steel handles most of this, but some sites may:
- Rate limit requests
- Show CAPTCHAs (Steel can handle some)
- Return different HTML structures

### Dynamic Match Scoring

Each property gets a "match score" (0-10) based on:
- Keyword matches in name, description, and location
- Price (cheaper = higher score)

Keywords come from:
- `--keywords` argument if provided
- Otherwise, extracted from `--query` argument

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

## Advanced Usage

### Different Websites

```bash
# Airbnb
python PropertyFinder.py --url "https://www.airbnb.com/s/{location}/homes?query={query}" --location "Colorado" --query "cabin"

# VRBO
python PropertyFinder.py --url "https://www.vrbo.com/search?destination={query}" --query "Lake Tahoe"

# Custom site
python PropertyFinder.py --url "https://example.com/search?q={query}" --query "vacation rental"
```

### Custom Keywords for Better Scoring

```bash
# Define keywords that matter to you
python PropertyFinder.py \
  --url "https://www.airbnb.com/s/{location}/homes?query={query}" \
  --location "Colorado" \
  --query "cabin" \
  --keywords "secluded,pet-friendly,fireplace,hot-tub,mountain-view"
```

### Track Performance Over Time

Run multiple times and compare in Raindrop:
- Search speed trends
- Success rates
- Number of results by query

### Set Up Alerts

In Raindrop dashboard:
- Alert if no results found
- Alert if search takes >10s
- Alert on extraction failures

## Troubleshooting

### No results found
- Try different query terms
- Check if the URL template is correct
- Check Raindrop logs for `no_results` signal

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
