"""
Property Finder
Searches any website for properties/listings using Steel, monitored by Raindrop.
Includes semantic query search via Raindrop Query SDK.
"""

import os
import re
import json
import sys
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
load_dotenv()

from steel import Steel
import raindrop.analytics as raindrop
from raindrop_query import RaindropQuery

raindrop.init(os.getenv("RAINDROP_WRITE_KEY"))

# Lazy-initialized query client
_query_client = None

def get_query_client() -> RaindropQuery:
    """Get or create the Raindrop Query SDK client."""
    global _query_client
    if _query_client is None:
        api_key = os.getenv("RAINDROP_QUERY_API_KEY")
        if not api_key:
            raise ValueError("RAINDROP_QUERY_API_KEY not set in environment")
        _query_client = RaindropQuery(api_key=api_key)
    return _query_client


class PropertyFinder:
    """
    Steel manages the cloud browser session.
    steel.scrape() pulls clean text/HTML from each URL.
    Raindrop tracks every step with begin()/finish() and track_signal().
    """

    def __init__(self, keywords: List[str] = None):
        self.session_id = f"search_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.client = Steel(steel_api_key=os.getenv("STEEL_API_KEY"))
        self.session = None
        self.results: List[Dict] = []
        self.keywords = keywords or []

    # Raindrop helpers

    def _track(self, event: str, input_text: str, output_text: str, props: dict = None):
        """Log a discrete step to Raindrop."""
        raindrop.track_ai(
            user_id=self.session_id,
            event=event,
            input=input_text,
            output=output_text,
            properties={"session_id": self.session_id, **(props or {})},
        )

    def _signal(self, event_id: str, name: str, sentiment: str = "POSITIVE", props: dict = None):
        """Attach a signal/alert to an existing Raindrop event."""
        raindrop.track_signal(
            event_id=event_id,
            name=name,
            sentiment=sentiment,
            properties=props or {},
        )

    # Session lifecycle

    def start_session(self):
        t0 = datetime.now()
        self.session = self.client.sessions.create()
        duration = (datetime.now() - t0).total_seconds()

        self._track(
            event="session_started",
            input_text="Create Steel browser session",
            output_text=f"Session {self.session.id} ready in {duration:.2f}s",
            props={
                "steel_session_id": self.session.id,
                "viewer_url": self.session.session_viewer_url,
                "duration_seconds": duration,
            },
        )
        print(f"Steel session: {self.session.id}")
        print(f"Watch live: {self.session.session_viewer_url}")

    def end_session(self):
        if self.session:
            self.client.sessions.release(self.session.id)
            self._track(
                event="session_released",
                input_text=f"Release session {self.session.id}",
                output_text="Session released",
            )
            print("Session released")

    # Scraping

    def scrape_url(self, url: str) -> str:
        """
        Use steel.scrape() to pull page content as clean text.
        Steel handles JS rendering, anti-bot protection, and CAPTCHAs.
        """
        interaction = raindrop.begin(
            user_id=self.session_id,
            event="page_scrape",
            input=f"Scrape URL: {url}",
            properties={"url": url},
        )

        try:
            print(f"Scraping: {url}")
            t0 = datetime.now()

            result = self.client.scrape(
                url=url,
                format=["html"],  # return full rendered HTML
                delay=3000,       # wait 3s for JS to render
            )
            content = result.content.html or ""

            duration = (datetime.now() - t0).total_seconds()

            print(f"Scraped {len(content)} chars in {duration:.2f}s")

            if duration > 8:
                self._signal(interaction.id, "slow_scrape", "NEGATIVE",
                             {"duration_seconds": duration})

            if len(content) < 500:
                self._signal(interaction.id, "thin_content", "NEGATIVE",
                             {"content_length": len(content)})

            interaction.set_properties({"duration_seconds": duration, "content_length": len(content)})
            interaction.finish(output=f"Scraped {len(content)} chars in {duration:.2f}s")

            return content

        except Exception as e:
            interaction.set_properties({"error": str(e)})
            interaction.finish(output=f"Scrape failed: {e}")
            self._signal(interaction.id, "scrape_failure", "NEGATIVE", {"error": str(e)})
            raise

    def _fetch_description(self, url: str) -> str:
        """Fetch property description from a listing page."""
        try:
            result = self.client.scrape(
                url=f"https://{url}",
                format=["html"],
                delay=2000,
            )
            html = result.content.html or ""

            # Extract description text (usually in meta tags or specific divs)
            desc_match = re.search(r'<meta[^>]+property="og:description"[^>]+content="([^"]+)"', html)
            if desc_match:
                return desc_match.group(1)

            # Fallback: look for description in JSON-LD
            json_matches = re.findall(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
            for match in json_matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, dict) and data.get("description"):
                        return data["description"]
                except:
                    continue

            return ""
        except Exception as e:
            self._track(
                event="description_fetch_failed",
                input_text=f"Fetch description from {url}",
                output_text=str(e),
            )
            return ""

    def parse_listings(self, html: str) -> List[Dict[str, Any]]:
        """
        Parse listing data out of HTML.
        Tries structured patterns first, falls back to regex.
        """
        interaction = raindrop.begin(
            user_id=self.session_id,
            event="parse_listings",
            input=f"Parse listings from {len(html)} chars of HTML",
        )

        listings = []

        try:
            # --- Strategy 1: JSON-LD structured data ---
            json_ld_matches = re.findall(
                r'<script[^>]+type="application/json"[^>]*>(.*?)</script>',
                html, re.DOTALL
            )

            for match in json_ld_matches:
                try:
                    data = json.loads(match)
                    extracted = self._extract_from_json(data)
                    listings.extend(extracted)
                except Exception:
                    continue

            if listings:
                self._track(
                    event="json_parse_success",
                    input_text="Parse JSON-LD from HTML",
                    output_text=f"{len(listings)} listings from JSON",
                    props={"count": len(listings), "method": "json_ld"},
                )

            # --- Strategy 2: Regex fallback if JSON-LD gave nothing ---
            if not listings:
                self._track(
                    event="json_parse_empty",
                    input_text="JSON-LD extraction",
                    output_text="No listings found, trying regex fallback",
                )
                listings = self._regex_parse(html)

            # Validate, score, deduplicate
            valid = []
            seen_names = set()
            for listing in listings:
                if self._is_valid(listing) and listing["name"] not in seen_names:
                    listing["match_score"] = self._calculate_score(listing)
                    valid.append(listing)
                    seen_names.add(listing["name"])

            self.results = valid

            sentiment = "POSITIVE" if valid else "NEGATIVE"
            signal = "results_found" if valid else "no_results"
            self._signal(interaction.id, signal, sentiment, {"count": len(valid)})

            interaction.finish(
                output=f"Parsed {len(valid)} valid listings",
                properties={"valid_count": len(valid), "raw_count": len(listings)},
            )

            return valid

        except Exception as e:
            interaction.finish(output=f"Parse failed: {e}")
            self._signal(interaction.id, "parse_failure", "NEGATIVE", {"error": str(e)})
            raise

    def _extract_from_json(self, data) -> List[Dict]:
        """Recursively hunt for listing objects in parsed JSON."""
        results = []

        if isinstance(data, dict):
            name = (data.get("name") or data.get("title") or "").strip()
            price_raw = (
                str(data.get("price") or data.get("priceString") or
                    data.get("priceValue") or "")
            )
            rating_raw = str(
                data.get("rating") or data.get("starRating") or
                data.get("avgRating") or ""
            )
            location = (
                data.get("location") or data.get("city") or
                data.get("neighborhood") or data.get("subtitle") or ""
            )
            if isinstance(location, dict):
                location = location.get("name") or location.get("city") or ""

            price_match = re.search(r"\$?(\d+)", str(price_raw))
            rating_match = re.search(r"(\d+\.?\d*)", str(rating_raw))

            if name and (price_match or rating_match):
                listing = {
                    "name": name,
                    "location": str(location) if location else "Unknown",
                    "price_per_night": int(price_match.group(1)) if price_match else None,
                    "rating": float(rating_match.group(1)) if rating_match else None,
                }
                results.append(listing)

            # Recurse into nested values
            for v in data.values():
                results.extend(self._extract_from_json(v))

        elif isinstance(data, list):
            for item in data:
                results.extend(self._extract_from_json(item))

        return results

    def _regex_parse(self, html: str) -> List[Dict]:
        # Strip tags to get plain text
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)

        # Find prices (looking for $XX patterns)
        prices = re.findall(r"\$(\d+)", text)

        # Find ratings (4.0-5.0 range)
        ratings = re.findall(r"\b([4-5]\.\d{1,2})\b", text)

        # Extract property URLs from HTML
        property_urls = []
        for url in re.findall(r'/rooms/(\d+)', html):
            property_urls.append(f"airbnb.com/rooms/{url}")
        property_urls = list(dict.fromkeys(property_urls))

        # Try to find location hints
        locations = re.findall(
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2},?\s+[A-Z]{2})",
            text
        )

        listings = []
        count = min(len(prices), len(ratings), 10)

        for i in range(count):
            url = property_urls[i] if i < len(property_urls) else None
            location = locations[i].strip() if i < len(locations) else "Unknown"

            listings.append({
                "name": url or f"Property {i + 1}",
                "location": location,
                "price_per_night": int(prices[i]),
                "rating": float(ratings[i]),
            })

        self._track(
            event="regex_parse",
            input_text="Regex fallback parse",
            output_text=f"{len(listings)} listings via regex",
            props={"count": len(listings), "prices_found": len(prices), "urls_found": len(property_urls)},
        )
        return listings

    # Scoring & validation

    def _is_valid(self, listing: Dict) -> bool:
        if not listing.get("name"):
            return False
        price = listing.get("price_per_night")
        if price is not None and not (5 < price < 2000):
            return False
        rating = listing.get("rating")
        if rating is not None and not (0 <= rating <= 5):
            return False
        return True

    def _calculate_score(self, listing: Dict) -> float:
        """Calculate match score based on keywords."""
        score = 5.0

        # Fetch description if we have a URL
        description = ""
        name = listing.get("name", "")
        if name.startswith("airbnb.com") or name.startswith("www.airbnb.com"):
            description = listing.get("description", "")
            if not description:
                description = self._fetch_description(name)
                listing["description"] = description  # Cache it

        # Combine text to check
        text_to_check = (description + " " + name + " " + listing.get("location", "")).lower()

        # Score based on keywords
        for keyword in self.keywords:
            if keyword.lower() in text_to_check:
                score += 0.5

        # Price bonus (cheaper = higher score)
        price = listing.get("price_per_night") or 150
        if price < 100:
            score += 2.0
        elif price < 150:
            score += 1.0

        return round(min(score, 10.0), 1)

    # Output

    def save(self, filename: str = "results.json"):
        out = {
            "session_id": self.session_id,
            "search_date": datetime.now().isoformat(),
            "total": len(self.results),
            "keywords": self.keywords,
            "results": self.results,
        }
        with open(filename, "w") as f:
            json.dump(out, f, indent=2)

        self._track(
            event="results_saved",
            input_text=f"Save {len(self.results)} listings",
            output_text=f"Written to {filename}",
            props={"filename": filename, "count": len(self.results)},
        )
        print(f"Saved to {filename}")

    def display(self, results: List[Dict]):
        print("\n" + "=" * 65)
        print("RESULTS - Ranked by Match Score")
        print("=" * 65)

        if not results:
            print("No results found.")
            return

        for i, r in enumerate(results, 1):
            price_str = f"${r['price_per_night']}/night" if r.get("price_per_night") else "Price unknown"
            rating_str = f"{r['rating']}/5.0" if r.get("rating") else "No rating"
            print(f"\n{i}. {r['name']}")
            print(f"   Location: {r.get('location', 'Unknown')}")
            print(f"   {price_str}   Rating: {rating_str}   Match Score: {r['match_score']}/10")

        top = results[0]
        print(f"\n{'=' * 65}")
        print(f"Top result: {top['name']}")
        print(f"   {top.get('location', 'Unknown')}")
        print("=" * 65)

    # Semantic Query Search (Raindrop Query SDK)

    def search_past_runs(self, query: str, limit: int = 10):
        """
        Semantic search through past PropertyFinder sessions.
        Finds runs matching the query by meaning, not just keywords.
        """
        print(f"\nSearching past runs for: \"{query}\"")
        try:
            client = get_query_client()
            results = client.events.search(
                query=query,
                mode="semantic",
                search_in="assistant_output",
                limit=limit,
            )
            return results
        except Exception as e:
            print(f"Query failed: {e}")
            return None

    def find_similar(self, description: str, limit: int = 10):
        """
        Find past discoveries matching a description.
        Uses semantic search on user inputs and session data.
        """
        print(f"\nFinding results similar to: \"{description}\"")
        try:
            client = get_query_client()
            results = client.events.search(
                query=description,
                mode="semantic",
                search_in="user_input",
                limit=limit,
            )
            return results
        except Exception as e:
            print(f"Query failed: {e}")
            return None

    def find_issues(self, limit: int = 10):
        """
        Find sessions with failures, slow scrapes, or other issues.
        """
        print(f"\nFinding sessions with issues...")
        try:
            client = get_query_client()
            results = client.events.search(
                query="slow scrape failure error timeout problem",
                mode="semantic",
                search_in="assistant_output",
                limit=limit,
            )
            return results
        except Exception as e:
            print(f"Query failed: {e}")
            return None

    def display_query_results(self, results, title: str = "Query Results"):
        """Pretty print semantic search results."""
        print("\n" + "=" * 65)
        print(f"{title}")
        print("=" * 65)

        # Handle Pydantic model response from raindrop-query SDK
        if hasattr(results, 'data'):
            items = results.data
        elif isinstance(results, list):
            items = results
        else:
            items = []

        if not items:
            print("No results found. (Events may take a few minutes to index)")
            return

        for i, r in enumerate(items, 1):
            # Handle Pydantic model - use correct field names from raindrop-query SDK
            event_name = getattr(r, 'event_name', 'unknown')
            user_input = getattr(r, 'user_input', '')[:80]
            assistant_output = getattr(r, 'assistant_output', '')[:80]
            timestamp = str(getattr(r, 'timestamp', ''))
            session = getattr(r, 'user_id', 'unknown')
            props = getattr(r, 'properties', {}) or {}
            relevance = getattr(r, 'relevance_score', 0)

            print(f"\n{i}. [{event_name}] {timestamp}")
            print(f"   Session: {session}")
            print(f"   Input: {user_input}")
            print(f"   Output: {assistant_output}")
            if props:
                print(f"   Props: {props}")
            print(f"   Relevance: {relevance:.2f}")

        print("\n" + "=" * 65)

    # Run

    def run(self, url: str, query: str, location: str = None):
        """Run the property finder with a URL template."""
        # Build URL from template
        try:
            final_url = url.format(query=query, location=location or "")
        except KeyError:
            # If template doesn't have all placeholders, use as-is
            final_url = url

        print("\n" + "=" * 65)
        print("PROPERTY FINDER")
        print("=" * 65)
        print(f"URL      : {final_url}")
        print(f"Query    : {query}")
        print(f"Keywords : {self.keywords}")
        print(f"Session  : {self.session_id}")
        print("=" * 65)

        run_interaction = raindrop.begin(
            user_id=self.session_id,
            event="property_finder_run",
            input=f"Find properties at {final_url}",
            properties={"url": final_url, "query": query, "keywords": self.keywords},
        )

        try:
            self.start_session()
            html = self.scrape_url(final_url)
            listings = self.parse_listings(html)
            ranked = sorted(listings, key=lambda x: x.get("match_score", 0), reverse=True)
            self.save()

            top_name = ranked[0]["name"] if ranked else "none"
            run_interaction.finish(
                output=f"Found {len(ranked)} results. Top: {top_name}",
                properties={"results_found": len(ranked)},
            )
            self._signal(run_interaction.id, "task_success", "POSITIVE",
                         {"results_found": len(ranked)})

            self.display(ranked)
            return ranked

        except Exception as e:
            run_interaction.finish(output=f"Failed: {e}")
            self._signal(run_interaction.id, "task_failure", "NEGATIVE", {"error": str(e)})
            print(f"\nFailed: {e}")
            raise

        finally:
            self.end_session()
            raindrop.flush()
            print(f"\nRaindrop session: {self.session_id}")

# Entry point

def print_usage():
    print("""
Property Finder - Usage:

  python PropertyFinder.py --url <url_template> --query <search_term> [options]
  python PropertyFinder.py --query <text>                           # Semantic search past runs
  python PropertyFinder.py --similar <text>                         # Find similar discoveries
  python PropertyFinder.py --issues                                 # Find sessions with problems

Required Arguments:
  --url      URL template with {query} and {location} placeholders
  --query    Search term (used for URL and scoring keywords)

Optional Arguments:
  --location    Location filter (default: none)
  --keywords    Scoring keywords, comma-separated (default: use query terms)

URL Template Examples:
  --url "https://www.airbnb.com/s/{location}/homes?query={query}"
  --url "https://example.com/search?q={query}"
  --url "https://site.com/listings?term={query}&area={location}"

Examples:
  python PropertyFinder.py --url "https://www.airbnb.com/s/{location}/homes?query={query}" --location "Colorado" --query "cabin"
  python PropertyFinder.py --url "https://example.com/search?q={query}" --query "beach house" --keywords "beach,ocean,waterfront"
  python PropertyFinder.py --query "colorado cabin results"
  python PropertyFinder.py --similar "secluded waterfront cabin"
  python PropertyFinder.py --issues
""")


def main():
    parser = argparse.ArgumentParser(
        description="Property Finder - Search any website for properties/listings",
        add_help=False,
    )
    parser.add_argument("--url", help="URL template with {query} and {location} placeholders")
    parser.add_argument("--query", help="Search term")
    parser.add_argument("--location", help="Location filter", default="")
    parser.add_argument("--keywords", help="Scoring keywords (comma-separated)")
    parser.add_argument("--similar", help="Find similar past discoveries")
    parser.add_argument("--issues", action="store_true", help="Find sessions with problems")
    parser.add_argument("--help", "-h", action="store_true", help="Show usage")

    args = parser.parse_args()

    # Show help
    if args.help:
        print_usage()
        return

    # Parse keywords
    keywords = []
    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]

    agent = PropertyFinder(keywords=keywords)

    # --query mode (without --url): semantic search past runs
    if args.query and not args.url:
        results = agent.search_past_runs(args.query)
        agent.display_query_results(results, f"Semantic Search: \"{args.query}\"")
        return

    # --similar mode: find similar discoveries
    if args.similar:
        results = agent.find_similar(args.similar)
        agent.display_query_results(results, f"Similar Results: \"{args.similar}\"")
        return

    # --issues mode: find problematic sessions
    if args.issues:
        results = agent.find_issues()
        agent.display_query_results(results, "Sessions with Issues")
        return

    # Scrape mode: require --url and --query
    if args.url and args.query:
        # If no keywords provided, extract from query
        if not keywords:
            keywords = args.query.lower().split()
            agent.keywords = keywords

        results = agent.run(url=args.url, query=args.query, location=args.location)
        print(f"\nDone! Found {len(results)} results.")
        print("See results.json for full data.")
        return

    # No valid arguments
    print_usage()


if __name__ == "__main__":
    main()
