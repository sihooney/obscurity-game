import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import quote


def get_random_wikipedia_page():
    """
    Fetches a random Wikipedia page title using the Wikipedia Random API.
    Ensures that the page is a valid article (not a talk page, category, help page, etc.).
    """
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "random",
        "rnlimit": 1,
        "format": "json"
    }
    while True:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            page_title = data['query']['random'][0]['title']
            # Fetch metadata to check if it's an article (namespace 0)
            page_info_url = "https://en.wikipedia.org/w/api.php"
            page_info_params = {
                "action": "query",
                "titles": page_title,
                "prop": "info",
                "format": "json"
            }

            page_info_response = requests.get(
                page_info_url, params=page_info_params)
            if page_info_response.status_code == 200:
                page_info = page_info_response.json()
                page_id = list(page_info['query']['pages'].keys())[0]
                namespace = page_info['query']['pages'][page_id].get(
                    'ns', None)

                # Check if the page is in the main namespace (namespace 0)
                if namespace == 0:
                    return page_title
                else:
                    print(
                        f"Skipping non-article page: {page_title}. Retrying...")
            else:
                print(f"Error fetching metadata for {page_title}. Retrying...")
        else:
            print("Error fetching random Wikipedia page.")
            return None


def get_wikipedia_pageviews(article_title, days=30):
    # Calculate start and end dates
    # yesterday (latest available data)
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days)).strftime("%Y%m%d")

    # Encode the article title for use in the URL
    encoded_title = quote(article_title.replace(" ", "_"), safe='')

    endpoint = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/all-agents/{encoded_title}/daily/{start_date}/{end_date}"

    headers = {
        'User-Agent': 'obscurity-game (hackathon project) sihaninfinite@gmail.com'
    }

    try:
        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()
        data = response.json()
        avg_views = sum(item["views"] for item in data["items"]) / 30
        return round(avg_views)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
    except KeyError:
        print("Unexpected data format or article not found.")
    return None


def get_hyperlinks_from_page(page_title):
    """
    Fetches and lists the hyperlinks on a Wikipedia page, excluding non-article links.
    """
    url = f"https://en.wikipedia.org/wiki/{page_title.replace(' ', '_')}"
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        links = []
        added = set()

        # Find all <a> tags with href attributes
        for link in soup.find_all('a', href=True):
            href = link['href']

            # Only consider links that start with '/wiki/', indicating it's a valid article
            if href.startswith('/wiki/') and ':' not in href:
                # Remove the '/wiki/' part to get the actual article title
                s = href[6:]
                if s not in added:
                    links.append(s)
                    added.add(s)

        return links
    else:
        print(f"Error: Unable to fetch {page_title}")
        return []


def play_game(clicks_allowed):
    """
    Starts the game with a random Wikipedia page and lets the user click through pages.
    """
    # Get a random Wikipedia page to start
    current_page = get_random_wikipedia_page()
    print(f"Starting the game on the Wikipedia page: {current_page}\n")

    total_clicks = 0
    while total_clicks < clicks_allowed:
        # Show the available links on the current page
        print(f"Click {total_clicks + 1}: You are on '{current_page}'")
        hyperlinks = get_hyperlinks_from_page(current_page)

        if not hyperlinks:
            print("No more links available. The game will end here.")
            break

        print(f"Links available (Choose a number to follow):")
        for idx, link in enumerate(hyperlinks, 1):
            print(f"{idx}. {link}")

        try:
            choice = int(input(f"Select a link (1-{len(hyperlinks)}): "))
            if 1 <= choice <= len(hyperlinks):
                current_page = hyperlinks[choice - 1]
            else:
                print("Invalid choice. Please try again.")
                continue
        except ValueError:
            print("Invalid input. Please enter a number.")
            continue

        total_clicks += 1
