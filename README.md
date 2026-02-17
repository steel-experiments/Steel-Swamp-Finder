# 🐊 Swamp Finder (Shrek Edition)

**"Get out of my swamp!"** - Now you can find your own!

A Steel-powered web automation agent that searches Airbnb for swamp-like properties, with full Raindrop monitoring for observability.

## What It Does

Searches Airbnb for swamp properties and extracts:
- ✅ **Property Name**
- ✅ **Location** (City/Region)
- ✅ **Price per Night**
- ✅ **Rating** (out of 5)
- ✅ **Swamp Score** (custom metric for swampiness!)

Results are ranked by "swampiness" and saved to `potential_swamps.json`.

## Why This Demo?

This showcases realistic web automation challenges:

### 🎯 Real-World Complexity
- **Semantic Search**: Airbnb doesn't do literal keyword matching - "swamp" might return bayous, wetlands, marsh properties
- **Dynamic Content**: Airbnb uses JavaScript rendering
- **Anti-Bot Detection**: Major sites have protection
- **Complex DOM**: Real-world HTML structure parsing

### 📊 Monitoring Points
Every action is logged to Raindrop:
- Browser initialization timing
- Page load performance
- Search query execution
- Listing extraction success/failure
- Data validation
- File save operations

### 🚨 Signals for Alerts
- `task_success` / `task_failure` - Overall outcome
- `swamps_discovered` - Found results
- `no_results_found` - Empty search
- `slow_page_load` - Performance issues (>5s)
- `extraction_failure` - Scraping problems
- `file_save_failure` - Output issues

## Setup

### 1. Install Dependencies

```bash
pip install steel-browser raindrop-ai python-dotenv
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
```

**Note**: Raindrop uses `RAINDROP_WRITE_KEY` (not API_KEY). Get your write key from https://app.raindrop.ai

### 4. Run It!

```bash
python swamp_finder.py
```

## Example Output

```
🐊 SWAMP FINDER (Shrek Edition)
======================================================================
📍 Searching for swamps in: Louisiana
📊 Session ID: swamp_search_20260216_143022
======================================================================

🌐 Browser started (session: abc123)
🔍 Searching Airbnb for swamps in Louisiana...
✅ Page loaded in 2.34s
📋 Extracting property listings...
✅ Found 5 potential swamps!
💾 Results saved to potential_swamps.json
🔒 Browser closed

======================================================================
🏆 POTENTIAL SWAMPS (Ranked by Swampiness)
======================================================================

1. Secluded Bayou Cabin - Perfect for Ogres
   📍 Honey Island Swamp, Louisiana
   💰 $89/night
   ⭐ 4.87/5.0
   🐊 Swamp Score: 9.5/10

2. Off-Grid Swamp Cottage
   📍 Jean Lafitte, Louisiana
   💰 $95/night
   ⭐ 4.68/5.0
   🐊 Swamp Score: 9.2/10

3. Private Marsh House with Boat Access
   📍 Manchac Swamp, Louisiana
   💰 $110/night
   ⭐ 4.75/5.0
   🐊 Swamp Score: 8.9/10

...

======================================================================
🧅 Shrek recommends: Secluded Bayou Cabin - Perfect for Ogres
   'Honey Island Swamp, Louisiana' - Now that's a proper swamp!
======================================================================

📈 Raindrop Session: swamp_search_20260216_143022
   Check your Raindrop dashboard for full execution trace
======================================================================
```

## Raindrop Monitoring Dashboard

### Event Timeline

```
[10:30:01] task_started (location: Louisiana)
[10:30:01] browser_start_requested
[10:30:03] browser_started (duration: 2.1s, session: abc123)
[10:30:03] airbnb_search_started (location: Louisiana, search_term: swamp)
[10:30:03] navigation_to_airbnb (url: https://airbnb.com/s/...)
[10:30:05] airbnb_page_loaded (duration: 2.34s)
[10:30:05] extraction_started
[10:30:06] page_scraped (content_length: 145832)
[10:30:06] parsing_listings
[10:30:06] listings_parsed (total_found: 5, validated: 5)
[10:30:06] listings_extracted (count: 5)
[10:30:06] ranking_started (swamp_count: 5)
[10:30:06] ranking_completed (top_swamp: Secluded Bayou Cabin)
[10:30:06] saving_results (filename: potential_swamps.json)
[10:30:06] results_saved (file_size: 1247 bytes)
[10:30:06] browser_close_requested
[10:30:07] browser_closed
[10:30:07] task_completed (success: true, duration: 6.2s, swamps_found: 5)
```

### Signal Alerts

```
✅ swamps_discovered (count: 5)
✅ task_success (swamps_found: 5, duration: 6.2s)
```

### Queries You Can Run in Raindrop

- `event:extraction_failed` - See all scraping failures
- `signal:slow_page_load` - Find performance issues
- `swamps_found > 0` - Successful searches
- `duration_seconds > 10` - Slow executions
- `session_id:swamp_search_20260216_143022` - View specific run

## Output File

Results are saved to `potential_swamps.json`:

```json
{
  "session_id": "swamp_search_20260216_143022",
  "search_date": "2026-02-16T14:30:07",
  "total_swamps": 5,
  "swamps": [
    {
      "name": "Secluded Bayou Cabin - Perfect for Ogres",
      "location": "Honey Island Swamp, Louisiana",
      "price_per_night": 89,
      "rating": 4.87,
      "swamp_score": 9.5
    },
    ...
  ]
}
```

## Important Notes

### ⚠️ Real Scraping Challenges

**Airbnb's DOM changes frequently**, so the selectors may need updates. The agent handles this by:

1. **Trying multiple selector patterns** - If one breaks, tries alternatives
2. **Fallback to regex parsing** - Can extract data even if selectors fail
3. **Comprehensive logging** - Raindrop tracks which selectors work/fail
4. **Graceful degradation** - Returns what it can find rather than crashing

**Anti-bot protection**: Steel handles most of this, but Airbnb may:
- Rate limit requests
- Show CAPTCHAs (Steel can handle some)
- Return different HTML structures

**Check Raindrop logs** to see which extraction method succeeded!

### 🔧 Real Airbnb Scraping with Steel

The agent uses **real Steel scraping** with multiple strategies:

1. **Structured Selectors**: Tries multiple Airbnb selector patterns
   - `[itemprop="itemListElement"]`
   - `[data-testid="card-container"]`
   - `[data-testid="listing-card-title"]`
   - And more fallback selectors

2. **Multi-Selector Approach**: If one selector fails, tries the next
3. **Fallback Parsing**: If structured selectors fail, parses full page HTML with regex
4. **Smart Data Extraction**: Extracts prices, ratings, locations from various HTML patterns

**Monitoring every extraction attempt:**
- Logs which selectors succeeded/failed
- Tracks how many elements found
- Records parsing fallbacks
- Validates extracted data

### 📊 Dynamic Swamp Scoring

Each property gets a "swamp score" (0-10) based on:
- Swamp keywords in name ("bayou", "marsh", "wetland", etc.)
- Location keywords
- Price (cheaper = more swampy!)
- State (Louisiana/Florida bonus points!)

This is calculated from **real scraped data**, not hardcoded.

## Monitoring Benefits

### Before Raindrop ❌
- Agent fails silently
- Don't know which step broke
- No performance tracking
- Hard to debug

### With Raindrop ✅
- See exact failure point
- Full execution timeline
- Performance metrics
- Search by natural language
- Alert on anomalies
- Compare runs

## Advanced Usage

### Different Locations

```bash
python swamp_finder.py
# Enter: Florida, Georgia, South Carolina, etc.
```

### Track Performance Over Time

Run multiple times and compare in Raindrop:
- Search speed trends
- Success rates
- Number of results by location

### A/B Test Search Terms

Modify the agent to try different keywords:
- "swamp"
- "bayou"
- "wetland"
- "marsh"

Compare which gets better results!

### Set Up Alerts

In Raindrop dashboard:
- Alert if no swamps found
- Alert if search takes >10s
- Alert on extraction failures

## Troubleshooting

### No results found
- Try different locations (Louisiana is best for swamps!)
- Airbnb's search might not match "swamp" in some areas
- Check Raindrop logs for `no_results_found` signal

### Slow page loads
- Check Raindrop for `slow_page_load` signals
- Airbnb can be slow, especially with images loading
- Steel handles this automatically with timeouts

### Browser won't start
- Verify your Steel API key is correct
- Check you have browser hours remaining
- Look for `browser_start_failed` event in Raindrop

## Next Steps

1. **Real Airbnb scraping**: Replace mock data with actual DOM parsing
2. **More locations**: Batch search multiple regions
3. **Price filtering**: Only show swamps under $100/night
4. **Availability checking**: Check dates and calendar
5. **Image extraction**: Download swamp photos
6. **Comparison tool**: Compare prices across locations
7. **Alerting**: Get notified when new swamps appear

## Shrek's Seal of Approval 🧅

*"This is exactly what I needed to find my next vacation home.*  
— Shrek, Professional Swamp Dweller

## Resources

- [Steel Documentation](https://docs.steel.dev)
- [Raindrop Documentation](https://docs.raindrop.ai)
- [Airbnb Search URL Format](https://www.airbnb.com/s/location/homes?query=term)