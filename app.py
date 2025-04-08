from flask import Flask, render_template, request, redirect, url_for, session
from game import get_random_wikipedia_page, get_hyperlinks_from_page, get_wikipedia_pageviews
import re
import requests

app = Flask(__name__)
app.secret_key = 'somethingsecret'


@app.route('/')
def index():
    return render_template('index.html', error=None)


@app.route('/start', methods=['POST'])
def start_game():
    url = request.form.get('url', '').strip()
    try:
        clicks = int(request.form.get('clicks', 3))
        if not (1 <= clicks <= 10):
            raise ValueError
    except ValueError:
        return render_template('index.html', error="Click count must be between 1 and 10.")

    if url:
        # Validate pasted URL
        match = re.match(r'^https?://en\.wikipedia\.org/wiki/([^#?]+)$', url)
        if match:
            article_title = match.group(1).replace('_', ' ')
            api_url = "https://en.wikipedia.org/w/api.php"
            params = {
                "action": "query",
                "titles": article_title,
                "prop": "info",
                "format": "json"
            }
            response = requests.get(api_url, params=params)
            if response.status_code == 200:
                data = response.json()
                page = list(data["query"]["pages"].values())[0]
                if page.get("ns", -1) == 0:
                    session['clicks'] = 0
                    session['max_clicks'] = clicks
                    session['page'] = article_title
                    return redirect(url_for('game'))
                else:
                    error = "That link is not a valid Wikipedia article."
            else:
                error = "Failed to validate the article. Please try again."
        else:
            error = "Please enter a valid Wikipedia article URL."
        return render_template('index.html', error=error)
    else:
        # Use random article
        start_page = get_random_wikipedia_page()
        session['clicks'] = 0
        session['max_clicks'] = clicks
        session['page'] = start_page
        return redirect(url_for('game'))


@app.route('/game', methods=['GET', 'POST'])
def game():
    if request.method == 'POST':
        choice = request.form.get('link')
        if choice:
            session['page'] = choice
            session['clicks'] += 1

    current_page = session.get('page', None)
    clicks = session.get('clicks', 0)
    max_clicks = session.get('max_clicks', 3)

    links = get_hyperlinks_from_page(current_page)
    game_over = clicks >= max_clicks or not links

    if game_over:
        views = get_wikipedia_pageviews(current_page)
        return render_template('game.html', current_page=current_page, clicks=clicks, max_clicks=max_clicks, links=[], views=views, game_over=True)

    return render_template('game.html', current_page=current_page, clicks=clicks, max_clicks=max_clicks, links=links, views=None, game_over=False)


if __name__ == '__main__':
    app.run(debug=True)
