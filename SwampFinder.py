
"""
Ogres Swamp Finder Agent
Uses Steel to search Airbnb for swamp-like properties and monitors with Raindrop
"""

import os
import asyncio
import json
import re
from datetime import datetime
from typing import List, Dict, Any

try:
    from steel import Steel
    STEEL_AVAILABLE = True
except ImportError:
    STEEL_AVAILABLE = False
    print("⚠️  Steel not installed. Run: pip install steel-browser")

try:
    from raindrop import Raindrop
    RAINDROP_AVAILABLE = True
except ImportError:
    RAINDROP_AVAILABLE = False
    print("⚠️  Raindrop not installed. Run: pip install raindrop-ai")


class SwampFinder:
    """
    Shrek-approved swamp hunting agent!
    
    Searches Airbnb for swamp-like properties and extracts:
    - Property name
    - Location
    - Price per night
    - Rating
    
    All actions monitored via Raindrop for observability
    """
    
    def __init__(self):
        self.session_id = f"swamp_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.task_name = "swamp_finder"
        self.steel = None
        self.browser_session = None
        self.swamps_found = []
        
        # Initialize Raindrop
        if RAINDROP_AVAILABLE and os.getenv("RAINDROP_API_KEY"):
            self.raindrop = Raindrop(api_key=os.getenv("RAINDROP_API_KEY"))
            print("✅ Raindrop monitoring enabled")
        else:
            raise RuntimeError("Raindrop is required")
        
        # Initialize Steel
        if STEEL_AVAILABLE and os.getenv("STEEL_API_KEY"):
            self.steel = Steel(steel_api_key=os.getenv("STEEL_API_KEY"))
            print("✅ Steel browser automation enabled")
        else:
            raise RuntimeError("Steel is required. Install: pip install steel-browser")
    
    def log_event(self, event_name: str, **kwargs):
        """Log event to Raindrop"""
        data = {
            "session_id": self.session_id,
            "task_name": self.task_name,
            "event": event_name,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        self.raindrop.log(data)
    
    def signal(self, signal_name: str, **kwargs):
        """Send signal to Raindrop"""
        data = {
            "session_id": self.session_id,
            "task_name": self.task_name,
            **kwargs
        }
        self.raindrop.signal(signal_name, data)
    
    async def start_browser(self):
        """Initialize Steel browser"""
        self.log_event("browser_start_requested")
        start_time = datetime.now()
        
        try:
            self.browser_session = await self.steel.sessions.create()
            duration = (datetime.now() - start_time).total_seconds()
            
            self.log_event("browser_started",
                          steel_session_id=self.browser_session.id,
                          duration_seconds=duration)
            
            print(f"🌐 Browser started (session: {self.browser_session.id})")
            
        except Exception as e:
            self.log_event("browser_start_failed", error=str(e))
            self.signal("browser_failure", error=str(e))
            raise
    
    async def search_airbnb(self, location: str = "Louisiana"):
        """
        Search Airbnb for swamp-like properties
        
        Note: Airbnb uses semantic search, so "swamp" might return:
        - Actual swamps
        - Bayous
        - Wetlands
        - Rural/nature properties
        - Lake/marsh areas
        """
        self.log_event("airbnb_search_started", 
                      location=location,
                      search_term="swamp")
        
        try:
            # Construct Airbnb search URL
            # Format: airbnb.com/s/{location}/homes?query=swamp
            search_query = "swamp"
            url = f"https://www.airbnb.com/s/{location}/homes?query={search_query}"
            
            print(f"🔍 Searching Airbnb for swamps in {location}...")
            self.log_event("navigation_to_airbnb", url=url)
            
            start_time = datetime.now()
            await self.steel.sessions.navigate(
                session_id=self.browser_session.id,
                url=url
            )
            duration = (datetime.now() - start_time).total_seconds()
            
            self.log_event("airbnb_page_loaded", 
                          duration_seconds=duration,
                          url=url)
            
            # Monitor slow loads
            if duration > 5:
                self.signal("slow_page_load",
                           url=url,
                           duration_seconds=duration)
            
            print(f"✅ Page loaded in {duration:.2f}s")
            
        except Exception as e:
            self.log_event("airbnb_navigation_failed", 
                          error=str(e),
                          url=url)
            self.signal("navigation_failure", error=str(e))
            raise
    
    async def extract_listings(self):
        """
        Extract property listings from Airbnb search results
        
        Extracts:
        - Name
        - Location
        - Price per night
        - Rating
        """
        self.log_event("extraction_started")
        print("📋 Extracting property listings...")
        
        try:
            # Scrape the search results page
            start_time = datetime.now()
            
            # Note: Actual selectors will vary based on Airbnb's HTML structure
            result = await self.steel.sessions.scrape(
                session_id=self.browser_session.id,
                selector="body"  # We'll parse this to find listings
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            raw_html = result.get("text", "")
            
            self.log_event("page_scraped",
                          duration_seconds=duration,
                          content_length=len(raw_html))
            
            # Parse listings using Steel's scraping capabilities
            listings = await self._parse_airbnb_listings(raw_html)
            
            self.swamps_found = listings
            
            self.log_event("listings_extracted",
                          count=len(listings),
                          duration_seconds=duration)
            
            if len(listings) == 0:
                self.signal("no_results_found",
                           search_term="swamp")
                print("⚠️  No swamps found!")
            else:
                self.signal("swamps_discovered",
                           count=len(listings))
                print(f"✅ Found {len(listings)} potential swamps!")
            
            return listings
            
        except Exception as e:
            self.log_event("extraction_failed", error=str(e))
            self.signal("extraction_failure", error=str(e))
            raise
    
    async def _parse_airbnb_listings(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Parse Airbnb HTML to extract listing data using Steel
        
        Uses Steel's scraping capabilities to extract real data from Airbnb
        """
        self.log_event("parsing_listings_started", content_length=len(html_content))
        
        listings = []
        
        try:
            # Wait for page to fully load
            await asyncio.sleep(2)
            
            # Method 1: Try to get listing cards using common Airbnb selectors
            # Airbnb uses different selectors, we'll try multiple approaches
            
            selectors_to_try = [
                '[itemprop="itemListElement"]',  # Common structured data selector
                '[data-testid="card-container"]',
                '.c4mnd7m',  # Airbnb listing card class (may change)
                '[data-testid="listing-card-title"]',
                '.l1ovpqvx',  # Another common class
            ]
            
            listing_elements = None
            selector_used = None
            
            # Try each selector until we find listings
            for selector in selectors_to_try:
                try:
                    result = await self.steel.sessions.scrape(
                        session_id=self.browser_session.id,
                        selector=selector
                    )
                    
                    # Check if we got results
                    if result and result.get("elements"):
                        listing_elements = result.get("elements", [])
                        selector_used = selector
                        self.log_event("selector_succeeded", 
                                      selector=selector,
                                      elements_found=len(listing_elements))
                        break
                    
                except Exception as e:
                    self.log_event("selector_failed", 
                                  selector=selector,
                                  error=str(e))
                    continue
            
            if not listing_elements:
                # Fallback: scrape entire page and parse manually
                self.log_event("using_fallback_parsing")
                return await self._parse_from_full_page()
            
            # Extract data from each listing element
            for idx, element in enumerate(listing_elements[:10]):  # Limit to first 10
                try:
                    listing_data = await self._extract_listing_data(element, idx)
                    if listing_data and self._validate_listing(listing_data):
                        listings.append(listing_data)
                        
                except Exception as e:
                    self.log_event("listing_extraction_failed",
                                  index=idx,
                                  error=str(e))
                    continue
            
            self.log_event("listings_parsed",
                          selector_used=selector_used,
                          total_found=len(listing_elements),
                          validated=len(listings))
            
            return listings
            
        except Exception as e:
            self.log_event("parsing_failed", error=str(e))
            self.signal("parsing_failure", error=str(e))
            
            # Return empty list rather than failing completely
            return []
    
    async def _extract_listing_data(self, element: Dict, index: int) -> Dict[str, Any]:
        """Extract structured data from a single listing element"""
        
        listing = {}
        
        try:
            # Extract title/name
            # Try multiple title selectors
            title_selectors = [
                '[data-testid="listing-card-title"]',
                '.t1jojoys',
                '[itemprop="name"]',
                'h3',
                '.fb4nyux'
            ]
            
            for selector in title_selectors:
                try:
                    title_result = await self.steel.sessions.scrape(
                        session_id=self.browser_session.id,
                        selector=selector
                    )
                    if title_result and title_result.get("text"):
                        listing["name"] = title_result["text"].strip()
                        break
                except:
                    continue
            
            # Extract price
            price_selectors = [
                '[data-testid="price-availability-row"]',
                '._1p7iugi',
                '.a8jt5op',
                '[itemprop="price"]'
            ]
            
            for selector in price_selectors:
                try:
                    price_result = await self.steel.sessions.scrape(
                        session_id=self.browser_session.id,
                        selector=selector
                    )
                    if price_result and price_result.get("text"):
                        price_text = price_result["text"]
                        # Parse price from text like "$89 night" or "$89"
                        import re
                        price_match = re.search(r'\$(\d+)', price_text)
                        if price_match:
                            listing["price_per_night"] = int(price_match.group(1))
                            break
                except:
                    continue
            
            # Extract rating
            rating_selectors = [
                '[data-testid="listing-card-subtitle"]',
                '._1s0r73o',
                '[aria-label*="rating"]',
                '[itemprop="ratingValue"]'
            ]
            
            for selector in rating_selectors:
                try:
                    rating_result = await self.steel.sessions.scrape(
                        session_id=self.browser_session.id,
                        selector=selector
                    )
                    if rating_result and rating_result.get("text"):
                        rating_text = rating_result["text"]
                        # Parse rating from text like "4.87 (123 reviews)"
                        import re
                        rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                        if rating_match:
                            rating_val = float(rating_match.group(1))
                            if 0 <= rating_val <= 5:
                                listing["rating"] = rating_val
                                break
                except:
                    continue
            
            # Extract location (if available in subtitle or description)
            location_selectors = [
                '[data-testid="listing-card-subtitle"]',
                '._1d1xx3f'
            ]
            
            for selector in location_selectors:
                try:
                    loc_result = await self.steel.sessions.scrape(
                        session_id=self.browser_session.id,
                        selector=selector
                    )
                    if loc_result and loc_result.get("text"):
                        listing["location"] = loc_result["text"].strip()
                        break
                except:
                    continue
            
            # Calculate swamp score based on keywords in title/location
            listing["swamp_score"] = self._calculate_swamp_score(listing)
            
            self.log_event("listing_extracted",
                          index=index,
                          has_name=bool(listing.get("name")),
                          has_price=bool(listing.get("price_per_night")),
                          has_rating=bool(listing.get("rating")))
            
            return listing
            
        except Exception as e:
            self.log_event("listing_data_extraction_failed",
                          index=index,
                          error=str(e))
            return {}
    
    async def _parse_from_full_page(self) -> List[Dict[str, Any]]:
        """
        Fallback: Parse listings from full page HTML
        Uses regex and text parsing when structured selectors fail
        """
        self.log_event("fallback_parsing_started")
        
        try:
            # Get full page content
            result = await self.steel.sessions.scrape(
                session_id=self.browser_session.id,
                selector="body"
            )
            
            html = result.get("text", "")
            
            # Use regex to find price patterns, titles, etc.
            import re
            
            # Find all prices
            prices = re.findall(r'\$(\d+)\s*(?:night|per night)', html)
            
            # Find potential listing titles (look for capitalized phrases)
            # This is a heuristic approach
            titles = re.findall(r'([A-Z][a-z]+(?: [A-Z][a-z]+){1,5})', html)
            
            # Find ratings
            ratings = re.findall(r'(\d\.\d+)\s*\((\d+)\)', html)
            
            listings = []
            
            # Create listings from parsed data
            for i in range(min(len(prices), len(titles), 5)):  # Max 5 listings
                listing = {
                    "name": titles[i] if i < len(titles) else f"Property {i+1}",
                    "price_per_night": int(prices[i]) if i < len(prices) else 0,
                    "rating": float(ratings[i][0]) if i < len(ratings) else 0.0,
                    "location": "Location not available",
                    "swamp_score": 5.0  # Default score
                }
                
                listing["swamp_score"] = self._calculate_swamp_score(listing)
                
                if self._validate_listing(listing):
                    listings.append(listing)
            
            self.log_event("fallback_parsing_completed",
                          listings_found=len(listings))
            
            return listings
            
        except Exception as e:
            self.log_event("fallback_parsing_failed", error=str(e))
            return []
    
    def _calculate_swamp_score(self, listing: Dict[str, Any]) -> float:
        """
        Calculate swampiness score based on listing attributes
        
        Higher score = more swamp-like
        """
        score = 5.0  # Base score
        
        swamp_keywords = [
            'swamp', 'bayou', 'marsh', 'wetland', 'bog',
            'waterfront', 'lake', 'river', 'creek',
            'secluded', 'remote', 'rustic', 'cabin',
            'nature', 'wildlife', 'fishing', 'boat'
        ]
        
        # Check name for swamp keywords
        name = listing.get("name", "").lower()
        for keyword in swamp_keywords:
            if keyword in name:
                score += 1.0
        
        # Check location for swamp keywords
        location = listing.get("location", "").lower()
        for keyword in swamp_keywords:
            if keyword in location:
                score += 0.5
        
        # Bonus for Louisiana/Florida (swamp states!)
        if any(state in location for state in ['louisiana', 'florida', 'georgia']):
            score += 1.0
        
        # Lower price = more swampy (luxury resorts aren't swamps!)
        price = listing.get("price_per_night", 100)
        if price < 100:
            score += 1.0
        
        # Cap at 10
        return min(score, 10.0)
    
    def _validate_listing(self, listing: Dict[str, Any]) -> bool:
        """Validate that listing has required fields"""
        required_fields = ["name", "location", "price_per_night", "rating"]
        
        for field in required_fields:
            if field not in listing:
                self.log_event("listing_validation_failed",
                              reason=f"missing_field_{field}",
                              listing_name=listing.get("name", "unknown"))
                return False
        
        # Check price is reasonable
        if listing["price_per_night"] < 0 or listing["price_per_night"] > 1000:
            self.log_event("listing_validation_failed",
                          reason="unrealistic_price",
                          price=listing["price_per_night"])
            return False
        
        # Check rating is valid
        if listing["rating"] < 0 or listing["rating"] > 5:
            self.log_event("listing_validation_failed",
                          reason="invalid_rating",
                          rating=listing["rating"])
            return False
        
        return True
    
    def rank_swamps(self):
        """Rank swamps by swampiness (custom scoring)"""
        self.log_event("ranking_started", swamp_count=len(self.swamps_found))
        
        # Sort by swamp_score (descending)
        ranked = sorted(self.swamps_found, 
                       key=lambda x: x.get("swamp_score", 0), 
                       reverse=True)
        
        self.log_event("ranking_completed",
                      top_swamp=ranked[0]["name"] if ranked else None)
        
        return ranked
    
    def save_results(self, filename: str = "potential_swamps.json"):
        """Save results to file"""
        self.log_event("saving_results", 
                      filename=filename,
                      swamp_count=len(self.swamps_found))
        
        try:
            output = {
                "session_id": self.session_id,
                "search_date": datetime.now().isoformat(),
                "total_swamps": len(self.swamps_found),
                "swamps": self.swamps_found
            }
            
            with open(filename, 'w') as f:
                json.dump(output, f, indent=2)
            
            self.log_event("results_saved",
                          filename=filename,
                          file_size_bytes=os.path.getsize(filename))
            
            print(f"💾 Results saved to {filename}")
            
        except Exception as e:
            self.log_event("save_failed", error=str(e))
            self.signal("file_save_failure", error=str(e))
            raise
    
    async def close_browser(self):
        """Clean up browser session"""
        self.log_event("browser_close_requested")
        
        try:
            if self.browser_session:
                await self.steel.sessions.release(self.browser_session.id)
                self.log_event("browser_closed")
                print("🔒 Browser closed")
        except Exception as e:
            self.log_event("browser_close_failed", error=str(e))
    
    async def run(self, location: str = "Louisiana"):
        """
        Main execution flow
        
        1. Start browser
        2. Search Airbnb for swamps
        3. Extract listings
        4. Validate and rank
        5. Save results
        """
        self.log_event("task_started", location=location)
        task_start = datetime.now()
        
        print("\n" + "="*70)
        print("🐊 SWAMP FINDER (Shrek Edition)")
        print("="*70)
        print(f"📍 Searching for swamps in: {location}")
        print(f"📊 Session ID: {self.session_id}")
        print("="*70 + "\n")
        
        try:
            # Step 1: Start browser
            await self.start_browser()
            
            # Step 2: Search Airbnb
            await self.search_airbnb(location=location)
            
            # Step 3: Extract listings
            listings = await self.extract_listings()
            
            # Step 4: Rank swamps
            ranked_swamps = self.rank_swamps()
            
            # Step 5: Save results
            self.save_results()
            
            # Success!
            duration = (datetime.now() - task_start).total_seconds()
            self.log_event("task_completed",
                          success=True,
                          duration_seconds=duration,
                          swamps_found=len(listings))
            self.signal("task_success",
                       swamps_found=len(listings),
                       duration_seconds=duration)
            
            # Display results
            self._display_results(ranked_swamps)
            
            return ranked_swamps
            
        except Exception as e:
            duration = (datetime.now() - task_start).total_seconds()
            self.log_event("task_failed",
                          error=str(e),
                          duration_seconds=duration)
            self.signal("task_failure",
                       error=str(e))
            
            print(f"\n❌ Task failed: {e}")
            raise
            
        finally:
            await self.close_browser()
            
            print("\n" + "="*70)
            print(f"📈 Raindrop Session: {self.session_id}")
            print("   Check your Raindrop dashboard for full execution trace")
            print("="*70 + "\n")
    
    def _display_results(self, swamps: List[Dict[str, Any]]):
        """Pretty print the results"""
        print("\n" + "="*70)
        print("🏆 POTENTIAL SWAMPS (Ranked by Swampiness)")
        print("="*70 + "\n")
        
        if not swamps:
            print("No swamps found! Try a different location. 🤷")
            return
        
        for i, swamp in enumerate(swamps, 1):
            print(f"{i}. {swamp['name']}")
            print(f"   📍 {swamp['location']}")
            print(f"   💰 ${swamp['price_per_night']}/night")
            print(f"   ⭐ {swamp['rating']}/5.0")
            print(f"   🐊 Swamp Score: {swamp['swamp_score']}/10")
            print()
        
        # Shrek's recommendation
        top_swamp = swamps[0]
        print("="*70)
        print(f"🧅 Shrek recommends: {top_swamp['name']}")
        print(f"   '{top_swamp['location']}' - Now that's a proper swamp!")
        print("="*70)


async def main():
    """Run the Swamp Finder"""
    
    # Ask user for location
    print("\n Welcome to Ogres Swamp Finder !")
    print("\nWhere should we search for swamps?")
    print("Suggestions: Louisiana, Florida, Georgia, South Carolina")
    
    location = input("\nEnter location (press Enter for Louisiana): ").strip()
    if not location:
        location = "Louisiana"
    
    # Create and run agent
    agent = SwampFinder()
    results = await agent.run(location=location)
    
    print(f"\n✅ Found {len(results)} potential swamps!")
    print("📄 Check 'potential_swamps.json' for full details")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(main())