from flask import Flask, render_template, request, redirect, url_for, session, flash
from game import (
    get_random_wikipedia_page,
    get_hyperlinks_from_page,
    get_wikipedia_pageviews,
    validate_wikipedia_url,
    get_page_extract,
    get_page_categories
)
from dotenv import load_dotenv
import os

app = Flask(__name__)
load_dotenv()
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
# Set to True in production with HTTPS
app.config['SESSION_COOKIE_SECURE'] = True


@app.route('/')
def index():
    # Clear any existing game session
    session.pop('game_state', None)
    return render_template('index.html')


@app.route('/start', methods=['POST'])
def start_game():
    url = request.form.get('url', '').strip()

    try:
        clicks = int(request.form.get('clicks', 3))
        if not (1 <= clicks <= 10):
            flash("Click count must be between 1 and 10.", "error")
            return redirect(url_for('index'))
    except (ValueError, TypeError):
        flash("Invalid click count. Please enter a number between 1 and 10.", "error")
        return redirect(url_for('index'))

    # Initialize game state
    if url:
        # Validate and extract article title from URL
        article_title = validate_wikipedia_url(url)
        if not article_title:
            flash("Please enter a valid Wikipedia article URL (e.g., https://en.wikipedia.org/wiki/Python)", "error")
            return redirect(url_for('index'))
        start_page = article_title
    else:
        # Get random article
        start_page = get_random_wikipedia_page()
        if not start_page:
            flash("Failed to get a random Wikipedia page. Please try again.", "error")
            return redirect(url_for('index'))

    # Initialize game session
    session['game_state'] = {
        'current_page': start_page,
        'clicks_used': 0,
        'max_clicks': clicks,
        'path': [start_page],  # Track the path taken
        'start_page': start_page
    }

    return redirect(url_for('game'))


@app.route('/game')
def game():
    game_state = session.get('game_state')

    if not game_state:
        flash("No active game. Please start a new game.", "info")
        return redirect(url_for('index'))

    current_page = game_state['current_page']
    clicks_used = game_state['clicks_used']
    max_clicks = game_state['max_clicks']
    clicks_remaining = max_clicks - clicks_used

    # Check if game is over
    if clicks_used >= max_clicks:
        # Game over - show results
        views = get_wikipedia_pageviews(current_page)
        categories = get_page_categories(
            current_page)[:5]  # Get top 5 categories
        return render_template('result.html',
                               current_page=current_page,
                               views=views,
                               path=game_state['path'],
                               clicks_used=clicks_used,
                               max_clicks=max_clicks,
                               categories=categories)

    # Get page extract for context
    extract = get_page_extract(current_page, sentences=2)

    # Get available links using the API
    links = get_hyperlinks_from_page(current_page)

    if not links:
        # No links available - end game
        views = get_wikipedia_pageviews(current_page)
        categories = get_page_categories(current_page)[:5]
        flash("No more links available from this page!", "warning")
        return render_template('result.html',
                               current_page=current_page,
                               views=views,
                               path=game_state['path'],
                               clicks_used=clicks_used,
                               max_clicks=max_clicks,
                               categories=categories,
                               no_links=True)

    return render_template('game.html',
                           current_page=current_page,
                           extract=extract,
                           links=links,
                           clicks_used=clicks_used,
                           clicks_remaining=clicks_remaining,
                           max_clicks=max_clicks,
                           path=game_state['path'],
                           total_links=len(links))


@app.route('/navigate', methods=['POST'])
def navigate():
    game_state = session.get('game_state')

    if not game_state:
        flash("No active game. Please start a new game.", "info")
        return redirect(url_for('index'))

    next_page = request.form.get('next_page')

    if not next_page:
        flash("Invalid selection. Please try again.", "error")
        return redirect(url_for('game'))

    # Update game state
    game_state['current_page'] = next_page
    game_state['clicks_used'] += 1
    game_state['path'].append(next_page)
    session['game_state'] = game_state

    return redirect(url_for('game'))


@app.route('/reset')
def reset_game():
    session.pop('game_state', None)
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
