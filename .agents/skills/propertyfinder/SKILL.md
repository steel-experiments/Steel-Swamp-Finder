---
name: propertyfinder
description: Search and extract property listings from any website using Steel browser automation with AI-powered extraction. Use when the user wants to find apartments, houses, flats, or properties for sale/rent on sites like Airbnb, njuskalo.hr, Booking.com, or similar listing sites.
---

# PropertyFinder

A CLI tool that scrapes property listing websites, extracts listings using AI, and ranks results by relevance to your search.

## Quick Start

```bash
python3 PropertyFinder.py --url "<listing_url>" --prompt "<what you're looking for>"
```

**Example:**
```bash
python3 PropertyFinder.py --url "https://www.airbnb.com/s/Porec--Croatia/homes" --prompt "apartments in Porec Istria Croatia"
```

## Environment Setup

Before using PropertyFinder, ensure `.env` contains:

```env
STEEL_API_KEY=ste-...           # Cloud browser scraping
RAINDROP_WRITE_KEY=...          # Analytics tracking
RAINDROP_QUERY_API_KEY=...      # Semantic search of past runs
OPENAI_API_KEY=sk-...           # AI-powered extraction
```

Install dependencies:
```bash
pip install openai steel raindrop-analytics raindrop-query python-dotenv
```

## CLI Flags

### Scrape Mode (Primary Usage)

| Flag | Required | Description |
|------|----------|-------------|
| `--url` | Yes | URL to scrape (any property listing site) |
| `--prompt` | Yes | Natural language description of what to find |
| `--location` | No | Location parameter for URL templates |
| `--keywords` | No | Override auto-extracted scoring keywords (comma-separated) |

**Examples:**
```bash
# Airbnb search
python3 PropertyFinder.py --url "https://www.airbnb.com/s/Porec--Croatia/homes" --prompt "apartments for vacation rental"

# Njuskalo.hr (Croatian real estate)
python3 PropertyFinder.py --url "https://www.njuskalo.hr/prodaja-stanova/split" --prompt "flats between 80 and 100 square meters"

# With custom keywords for better scoring
python3 PropertyFinder.py --url "https://www.njuskalo.hr/prodaja-kuca/zagreb" --prompt "houses with gardens" --keywords "garden,backyard,outdoor,terasa,vrt"
```

### Semantic Search Mode

| Flag | Description |
|------|-------------|
| `--query <text>` | Search past runs semantically |
| `--similar <text>` | Find similar past discoveries |
| `--issues` | Find sessions with problems/failures |

**Examples:**
```bash
# Find past searches about cabins
python3 PropertyFinder.py --query "cabin colorado results"

# Find sessions that had issues
python3 PropertyFinder.py --issues

# Find similar properties to what you've searched before
python3 PropertyFinder.py --similar "waterfront with garden"
```

## How It Works

1. **Steel** launches a cloud browser, navigates to the URL, and scrapes rendered HTML
2. **AI** analyzes the HTML and extracts property listings (names, prices, locations, URLs, ratings)
3. **Scoring** ranks results based on keyword matches from your prompt
4. **Raindrop** tracks everything for later semantic search

## Output

- **Console**: Ranked results with match scores
- **results.json**: Full data in JSON format

Each result contains:
- `name` - Property title
- `location` - City/area
- `price` - Numeric price
- `currency` - EUR, USD, GBP, HRK
- `rating` - 0-5 scale if available
- `url` - Link to listing
- `match_score` - Relevance score (0-10)

## Expected Results by Site

| Site | Expected Listings | Notes |
|------|-------------------|-------|
| njuskalo.hr | 10-15 | Good extraction, Croatian real estate |
| airbnb.com | 10-11 | Good extraction with prices and ratings |
| booking.com | 2-3 | Heavy JS rendering, lower quality |
| idealista.com | 0 | Anti-bot protection |

## Troubleshooting

### Few or No Results

1. **Check traces**: `python3 PropertyFinder.py --issues`
2. **Search past runs**: `python3 PropertyFinder.py --query "extraction listings"`
3. **Watch the session**: Click the Steel session URL to see scraping in real-time

### Common Issues

- **"No results found"**: Site may have anti-bot protection or heavy JS rendering
- **Wrong prices**: Some sites load prices dynamically
- **Missing names**: HTML structure may not match expected patterns

### Using Raindrop Traces

When debugging, check these metrics in traces:
- `raw_count` vs `valid_count` - if raw is high but valid is low, validation may be filtering results
- `prices_found` and `urls_found` - indicates HTML quality
- Recent traces take a few minutes to index

## Adding New CLI Flags

To extend the tool:

1. Edit `main()` function's argparse section in `PropertyFinder.py`:
```python
parser.add_argument("--newflag", help="Description of new flag")
```

2. Handle the flag after parsing:
```python
if args.newflag:
    # Handle new flag
```

3. Update `print_usage()` to document it

## Workflow Tips

1. Start with a descriptive `--prompt` - keywords are auto-extracted for scoring
2. Check `results.json` for complete data
3. Use `--issues` to diagnose poor results
4. Use `--similar` to find matching past discoveries
5. Watch the Steel session URL to see scraping progress
