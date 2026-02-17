"""
🐊 Swamp Finder (Shrek Edition)
Searches Airbnb for swamp properties using Steel, monitored by Raindrop.
"""

import os
import re
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
load_dotenv()

from steel import Steel
import raindrop.analytics as raindrop

raindrop.init(os.getenv("RAINDROP_WRITE_KEY"))


class SwampFinder:
    """
    Steel manages the cloud browser session.
    steel.scrape() pulls clean text/HTML from each URL.
    Raindrop tracks every step with begin()/finish() and track_signal().
    """

    def __init__(self):
        self.session_id = f"swamp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.client = Steel(steel_api_key=os.getenv("STEEL_API_KEY"))
        self.session = None
        self.swamps: List[Dict] = []

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
        print(f"🌐 Steel session: {self.session.id}")
        print(f"👀 Watch live: {self.session.session_viewer_url}")

    def end_session(self):
        if self.session:
            self.client.sessions.release(self.session.id)
            self._track(
                event="session_released",
                input_text=f"Release session {self.session.id}",
                output_text="Session released",
            )
            print("🔒 Session released")

    # Scraping

    def scrape_airbnb(self, location: str) -> str:
        """
        Use steel.scrape() to pull Airbnb search results as clean text.
        Steel handles JS rendering, anti-bot protection, and CAPTCHAs.
        """
        url = f"https://www.airbnb.com/s/{location}/homes?query=swamp"

        interaction = raindrop.begin(
            user_id=self.session_id,
            event="airbnb_scrape",
            input=f"Scrape Airbnb swamp search: {url}",
            properties={"location": location, "url": url},
        )

        try:
            print(f"🔍 Scraping Airbnb for swamps in {location}...")
            t0 = datetime.now()

            result = self.client.scrape(
            url=url,
            format=["html"],  # return full rendered HTML
            delay=3000,       # wait 3s for JS to render listings
            )
            content = result.content.html or ""

            duration = (datetime.now() - t0).total_seconds()
            content = result.content.html or ""

            print(f"✅ Scraped {len(content)} chars in {duration:.2f}s")

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

    def parse_listings(self, html: str) -> List[Dict[str, Any]]:
        """
        Parse listing data out of Airbnb HTML.
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
            # Airbnb embeds listing data as JSON-LD in <script> tags
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
                    listing["swamp_score"] = self._swamp_score(listing)
                    valid.append(listing)
                    seen_names.add(listing["name"])

            self.swamps = valid

            sentiment = "POSITIVE" if valid else "NEGATIVE"
            signal = "swamps_found" if valid else "no_results"
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
            # Airbnb embeds pricing/listing data in various shapes
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
        """Last-resort regex extraction from raw HTML text."""
        # Strip tags to get plain text
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)

        prices = re.findall(r"\$(\d{2,4})\s*(?:per night|night|/night)?", text)
        ratings = re.findall(r"\b([4-5]\.\d{1,2})\b", text)  # Only realistic ratings 4.x–5.x

        listings = []
        for i in range(min(len(prices), len(ratings), 8)):
            listings.append({
                "name": f"Property {i + 1}",
                "location": "Unknown",
                "price_per_night": int(prices[i]),
                "rating": float(ratings[i]),
            })

        self._track(
            event="regex_parse",
            input_text="Regex fallback parse",
            output_text=f"{len(listings)} listings via regex",
            props={"count": len(listings)},
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

    def _swamp_score(self, listing: Dict) -> float:
        score = 5.0
        swamp_words = ["swamp", "bayou", "marsh", "wetland", "bog", "creek",
                       "waterfront", "lake", "river", "secluded", "remote",
                       "rustic", "cabin", "nature", "wildlife", "fishing"]

        name = listing.get("name", "").lower()
        loc = listing.get("location", "").lower()

        for word in swamp_words:
            if word in name:
                score += 1.0
            if word in loc:
                score += 0.5

        if any(s in loc for s in ["louisiana", "florida", "georgia", "mississippi"]):
            score += 1.5

        price = listing.get("price_per_night") or 150
        if price < 100:
            score += 1.0

        return round(min(score, 10.0), 1)

    # Output

    def save(self, filename: str = "potential_swamps.json"):
        out = {
            "session_id": self.session_id,
            "search_date": datetime.now().isoformat(),
            "total": len(self.swamps),
            "swamps": self.swamps,
        }
        with open(filename, "w") as f:
            json.dump(out, f, indent=2)

        self._track(
            event="results_saved",
            input_text=f"Save {len(self.swamps)} listings",
            output_text=f"Written to {filename}",
            props={"filename": filename, "count": len(self.swamps)},
        )
        print(f"💾 Saved to {filename}")

    def display(self, swamps: List[Dict]):
        print("\n" + "=" * 65)
        print("🏆 POTENTIAL SWAMPS — Ranked by Swampiness")
        print("=" * 65)

        if not swamps:
            print("No swamps found. Shrek is displeased. 🧅")
            return

        for i, s in enumerate(swamps, 1):
            price_str = f"${s['price_per_night']}/night" if s.get("price_per_night") else "Price unknown"
            rating_str = f"{s['rating']}/5.0" if s.get("rating") else "No rating"
            print(f"\n{i}. {s['name']}")
            print(f"   📍 {s.get('location', 'Unknown')}")
            print(f"   💰 {price_str}   ⭐ {rating_str}   🐊 Swamp Score: {s['swamp_score']}/10")

        top = swamps[0]
        print(f"\n{'=' * 65}")
        print(f"🧅 Shrek's pick: {top['name']}")
        print(f"   \"{top.get('location')}\" — Now THAT'S a swamp.")
        print("=" * 65)

    # Run

    def run(self, location: str = "Louisiana"):
        print("\n" + "=" * 65)
        print("🐊 SWAMP FINDER (Shrek Edition)")
        print("=" * 65)
        print(f"📍 Location : {location}")
        print(f"📊 Session  : {self.session_id}")
        print("=" * 65)

        run_interaction = raindrop.begin(
            user_id=self.session_id,
            event="swamp_finder_run",
            input=f"Find swamp Airbnb listings in {location}",
            properties={"location": location},
        )

        try:
            self.start_session()
            html = self.scrape_airbnb(location)
            listings = self.parse_listings(html)
            ranked = sorted(listings, key=lambda x: x.get("swamp_score", 0), reverse=True)
            self.save()

            top_name = ranked[0]["name"] if ranked else "none"
            run_interaction.finish(
                output=f"Found {len(ranked)} swamps. Top: {top_name}",
                properties={"swamps_found": len(ranked)},
            )
            self._signal(run_interaction.id, "task_success", "POSITIVE",
                         {"swamps_found": len(ranked)})

            self.display(ranked)
            return ranked

        except Exception as e:
            run_interaction.finish(output=f"Failed: {e}")
            self._signal(run_interaction.id, "task_failure", "NEGATIVE", {"error": str(e)})
            print(f"\n❌ Failed: {e}")
            raise

        finally:
            self.end_session()
            raindrop.flush()
            print(f"\n📈 Raindrop session: {self.session_id}")

# Entry point

def main():
    print("\n🐊 Welcome to Swamp Finder (Shrek Edition)!")
    print("Suggestions: Louisiana, Florida, Georgia, South Carolina, Mississippi")

    location = input("\nEnter location (press Enter for Louisiana): ").strip()
    if not location:
        location = "Louisiana"

    agent = SwampFinder()
    results = agent.run(location=location)
    print(f"\n✅ Done! Found {len(results)} potential swamps.")
    print("📄 See potential_swamps.json for full data.")


if __name__ == "__main__":
    main()