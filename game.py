import requests
from datetime import datetime, timedelta
from urllib.parse import quote, unquote
import re
import time
import json

# Wikimedia Analytics API documentation:
# https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/

# Wikipedia API endpoints
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIMEDIA_PAGEVIEWS_API = "https://wikimedia.org/api/rest_v1/metrics"

# User-Agent header is REQUIRED by Wikipedia API
# Must be descriptive and include contact info
USER_AGENT = "WikipediaObscurityGame/1.0 (https://github.com/yourusername/wiki-game; your-email@example.com) Python/requests"


def create_session():
    """
    Create a requests session with proper headers for Wikipedia API.
    Wikipedia requires a descriptive User-Agent header.
    """
    session = requests.Session()
    session.headers.update({
        'User-Agent': USER_AGENT,
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip, deflate'
    })
    return session


# Create a global session for reuse (more efficient)
wiki_session = create_session()


def validate_wikipedia_url(url):
    """
    Validates a Wikipedia URL and returns the article title if valid.
    Uses the MediaWiki API to verify the page exists and is a valid article.
    """
    # Match Wikipedia URL patterns
    patterns = [
        r'^https?://en\.wikipedia\.org/wiki/([^#?]+)',
        r'^https?://wikipedia\.org/wiki/([^#?]+)',
        r'^en\.wikipedia\.org/wiki/([^#?]+)',
        r'^wikipedia\.org/wiki/([^#?]+)'
    ]

    for pattern in patterns:
        match = re.match(pattern, url)
        if match:
            # Decode the article title from URL format
            article_title = unquote(match.group(1)).replace('_', ' ')

            # Use MediaWiki API to verify the page exists
            params = {
                "action": "query",
                "format": "json",
                "titles": article_title,
                "prop": "info",
                "inprop": "protection|url",
                "formatversion": "2"  # Use newer, cleaner format
            }

            try:
                response = wiki_session.get(
                    WIKIPEDIA_API, params=params, timeout=10)
                response.raise_for_status()

                data = response.json()
                pages = data.get("query", {}).get("pages", [])

                if pages:
                    page = pages[0]
                    # Check if page exists (no 'missing' key) and is in main namespace (ns=0)
                    if "missing" not in page and page.get("ns", -1) == 0:
                        # Return the normalized title from API
                        return page.get("title", article_title)

            except requests.RequestException as e:
                print(f"Error validating Wikipedia URL: {e}")
            except json.JSONDecodeError as e:
                print(f"Error parsing API response: {e}")

    return None


def get_random_wikipedia_page(max_attempts=5):
    """
    Fetches a random Wikipedia article using the MediaWiki API.
    Only returns articles from the main namespace (ns=0).
    """
    params = {
        "action": "query",
        "format": "json",
        "list": "random",
        "rnnamespace": "0",  # Main namespace only (articles)
        "rnlimit": "1",
        "formatversion": "2"
    }

    for attempt in range(max_attempts):
        try:
            response = wiki_session.get(
                WIKIPEDIA_API, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            random_pages = data.get('query', {}).get('random', [])

            if random_pages:
                title = random_pages[0].get('title')
                if title:
                    print(f"Got random page: {title}")
                    return title

        except requests.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_attempts - 1:
                time.sleep(1)  # Brief delay before retry
        except json.JSONDecodeError as e:
            print(f"Error parsing API response: {e}")

    return None


def get_wikipedia_pageviews(article_title, duration=30):
    """
    Gets the average daily pageviews for a Wikipedia article using the Wikimedia REST API.
    Returns None if unable to fetch data.
    """
    try:
        # Calculate date range (data might not be available for today/yesterday)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=duration)

        # Format dates as YYYYMMDD for API
        end_str = end_date.strftime("%Y%m%d")
        start_str = start_date.strftime("%Y%m%d")

        # Replace spaces with underscores and properly encode the title
        formatted_title = article_title.replace(' ', '_')
        encoded_title = quote(formatted_title, safe='')

        # Use Wikimedia REST API for pageviews
        endpoint = f"{WIKIMEDIA_PAGEVIEWS_API}/pageviews/per-article/en.wikipedia/all-access/all-agents/{encoded_title}/daily/{start_str}/{end_str}"

        response = wiki_session.get(endpoint, timeout=10)

        if response.status_code == 404:
            print(f"No pageview data available for: {article_title}")
            return None

        response.raise_for_status()

        data = response.json()
        items = data.get("items", [])

        if items:
            total_views = sum(item.get("views", 0) for item in items)
            avg_views = total_views / len(items) if len(items) > 0 else 0
            return round(avg_views)

    except requests.RequestException as e:
        print(f"Error fetching pageviews for '{article_title}': {e}")
    except json.JSONDecodeError as e:
        print(f"Error parsing pageview data: {e}")
    except Exception as e:
        print(f"Unexpected error fetching pageviews: {e}")

    return None


def get_hyperlinks_from_page(page_title, max_links=100000000):
    """
    Fetches the links from a Wikipedia page using the MediaWiki API.
    This is more reliable than scraping HTML and respects Wikipedia's guidelines.
    """
    try:
        links = []
        plcontinue = None

        # Use the API's links module to get all internal links
        while len(links) < max_links:
            params = {
                "action": "query",
                "format": "json",
                "titles": page_title,
                "prop": "links",
                "pllimit": "max",
                # Only get links to main namespace (articles)
                "plnamespace": "0",
                "formatversion": "2"
            }

            # Handle pagination
            if plcontinue:
                params["plcontinue"] = plcontinue

            response = wiki_session.get(
                WIKIPEDIA_API, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            pages = data.get("query", {}).get("pages", [])

            if not pages:
                break

            page = pages[0]

            # Check if page exists
            if "missing" in page:
                print(f"Page not found: {page_title}")
                return []

            # Extract links
            page_links = page.get("links", [])

            for link in page_links:
                link_title = link.get("title", "")
                if link_title and len(links) < max_links:
                    links.append({
                        'title': link_title,
                        'display': link_title  # For API results, title is already clean
                    })

            # Check if there are more results
            if "continue" in data and len(links) < max_links:
                plcontinue = data["continue"].get("plcontinue")
            else:
                break

        print(f"Found {len(links)} links from '{page_title}'")
        return links[:max_links]

    except requests.RequestException as e:
        print(f"Error fetching links for '{page_title}': {e}")
    except json.JSONDecodeError as e:
        print(f"Error parsing API response: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

    return []


def get_page_extract(page_title, sentences=3):
    """
    Gets a short extract/summary of a Wikipedia page using the MediaWiki API.
    This can be useful for showing a preview of the current page.
    """
    params = {
        "action": "query",
        "format": "json",
        "titles": page_title,
        "prop": "extracts",
        "exintro": True,  # Only get the introduction
        "explaintext": True,  # Get plain text (no wiki markup)
        "exsentences": sentences,  # Number of sentences to extract
        "formatversion": "2"
    }

    try:
        response = wiki_session.get(WIKIPEDIA_API, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        pages = data.get("query", {}).get("pages", [])

        if pages and "missing" not in pages[0]:
            return pages[0].get("extract", "")

    except Exception as e:
        print(f"Error getting page extract: {e}")

    return ""


def search_wikipedia(query, limit=10):
    """
    Search Wikipedia for articles matching a query.
    Returns a list of matching page titles.
    """
    params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": query,
        "srlimit": limit,
        "srnamespace": "0",  # Search only main namespace
        "formatversion": "2"
    }

    try:
        response = wiki_session.get(WIKIPEDIA_API, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        search_results = data.get("query", {}).get("search", [])

        return [result.get("title") for result in search_results if result.get("title")]

    except Exception as e:
        print(f"Error searching Wikipedia: {e}")

    return []


def get_page_categories(page_title, hidden=False):
    """
    Gets the categories a Wikipedia page belongs to.
    This can help determine how obscure a page is.
    """
    params = {
        "action": "query",
        "format": "json",
        "titles": page_title,
        "prop": "categories",
        "cllimit": "max",
        "formatversion": "2"
    }

    if not hidden:
        params["clshow"] = "!hidden"  # Exclude hidden categories

    try:
        response = wiki_session.get(WIKIPEDIA_API, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        pages = data.get("query", {}).get("pages", [])

        if pages and "missing" not in pages[0]:
            categories = pages[0].get("categories", [])
            return [cat.get("title", "").replace("Category:", "") for cat in categories]

    except Exception as e:
        print(f"Error getting categories: {e}")

    return []

def get_page_info(page_title):
    """
    Gets detailed information about a Wikipedia page.
    Returns a dictionary with various page properties.
    """
    params = {
        "action": "query",
        "format": "json",
        "titles": page_title,
        "prop": "info|pageprops",
        "inprop": "protection|talkid|watched|watchers|visitingwatchers|notificationtimestamp|subjectid|url|readable|preload|displaytitle",
        "formatversion": "2"
    }

    try:
        response = wiki_session.get(WIKIPEDIA_API, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        pages = data.get("query", {}).get("pages", [])

        if pages and "missing" not in pages[0]:
            return pages[0]

    except Exception as e:
        print(f"Error getting page info: {e}")

    return {}
