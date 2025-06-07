from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, get_flashed_messages
from database import DatabaseManager
from cobrapinger import load_config
import markdown
import re
from datetime import datetime
import calendar
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import functools
from feedgen.feed import FeedGenerator
from flask import make_response

app = Flask(__name__, static_folder='static')
config = load_config()

# Add min function to Jinja globals
app.jinja_env.globals.update(min=min)

db = DatabaseManager('db.sqlite')

@app.template_filter('markdown')
def markdown_filter(text):
    if not text:
        return ""
    return markdown.markdown(text, extensions=[
        'markdown.extensions.fenced_code',
        'markdown.extensions.tables',
        'markdown.extensions.nl2br',
        'markdown.extensions.sane_lists'
    ])

@app.template_filter('nl2br')
def nl2br(text):
    """Convert newlines to HTML line breaks."""
    if not text:
        return ""
    return text.replace('\n', '<br>')

@app.route('/')
def index():
    """Welcome page with latest video and random quote."""
    quote = db.get_random_quote()
    latest_video = db.get_latest_video()
    
    return render_template('index.html', active_page='home', quote=quote, latest_video=latest_video)

@app.route('/videos')
def videos():
    """Video listing page with filters."""
    page = request.args.get('page', 1, type=int)
    selected_channels = request.args.getlist('channels', type=int)
    
    channels = db.get_all_channels()
    result = db.get_all_videos(
        page=page, 
        channel_ids=selected_channels if selected_channels else None
    )
    
    # Get random quote
    quote = db.get_random_quote()
    
    return render_template('videos.html', active_page='videos', videos=result['videos'], total=result['total'], pages=result['pages'], current_page=page, channels=channels, selected_channels=selected_channels, quote=quote)

@app.route('/video/<int:video_id>')
def video_details(video_id):  # Changed function name to be more descriptive
    video = db.get_video_details(video_id)
    if not video:
        abort(404)
    
    comments = db.get_video_comments(video_id)
    can_comment = session.get('user_id') and db.can_user_comment(session['user_id'])
    
    return render_template('video.html', 
                         video=video, 
                         comments=comments,
                         can_comment=can_comment)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    
    if not query:
        return render_template('search.html', results=None)
        
    result = db.search_videos(query, page=page)
    return render_template(
        'search.html', 
        results=result['results'],
        query=query,
        total=result['total'],
        pages=result['pages'],
        current_page=page
    )

@app.route('/topic/<topic_name>')
def topic_videos(topic_name):
    page = request.args.get('page', 1, type=int)
    topic_id = db.get_topic_id(topic_name)
    
    if topic_id is None:
        return "Topic not found", 404
        
    result = db.get_videos_by_topic(topic_id, page=page)
    return render_template(
        'topic.html', 
        videos=result['videos'],
        total=result['total'],
        pages=result['pages'],
        current_page=page,
        topic=topic_name
    )

@app.route('/calendar')
@app.route('/calendar/<int:year>/<int:month>')
def calendar_view(year=None, month=None):
    if year is None:
        now = datetime.now()
        year = now.year
        month = now.month
        
    # Get calendar info
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    
    # Get videos for this month
    videos = db.get_videos_by_date(year, month)
    
    # Organize videos by day
    video_map = {}
    for video in videos:
        day = int(video['youtube_created_at'].split('-')[2].split('T')[0])
        if day not in video_map:
            video_map[day] = []
        video_map[day].append(video)
    
    # Calculate prev/next months
    prev_month = (month - 2) % 12 + 1
    prev_year = year - (1 if month == 1 else 0)
    next_month = month % 12 + 1
    next_year = year + (1 if month == 12 else 0)
    
    return render_template('calendar.html', active_page='calendar', calendar=cal, video_map=video_map, month=month, month_name=month_name, year=year, prev_month=prev_month, prev_year=prev_year, next_month=next_month, next_year=next_year)

@app.route('/topics')
def topic_cloud():
    """Show all topics in a tag cloud."""
    topics = db.get_topic_counts()  # We'll create this method
    return render_template('topics.html', active_page='topics', topics=topics)

@app.template_filter('formatdate')
def formatdate(date_str):
    """Format ISO date string to human readable format."""
    if not date_str:
        return ""
    try:
        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return date.strftime('%B %d, %Y')  # Example: January 1, 2024
    except ValueError:
        return date_str

@app.route('/request-invite', methods=['POST'])
def request_invite():
    # Get daily limit from config
    daily_limit = config.get('daily_invite_limit', 30)
    
    success, result = db.generate_invite_code(daily_limit)
    
    if success:
        flash(f'Your invite code is: {result}', 'success')
    else:
        flash(result, 'error')
    
    return redirect(url_for('register'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        invite_code = request.form['invite_code']

        # Validate invite code
        if not db.validate_invite_code(invite_code):
            return render_template('register.html', error='Invalid or used invite code')

        # Basic validation
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return render_template('register.html', error='Username can only contain letters, numbers, and underscores')
        
        if len(password) < 8:
            return render_template('register.html', error='Password must be at least 8 characters')

        try:
            # Create user
            password_hash = generate_password_hash(password)
            user_id = db.create_user(username, email, password_hash)
            
            # Mark invite code as used
            db.mark_invite_code_used(invite_code)
            
            # TODO: Set up user session
            return redirect(url_for('index'))
        except sqlite3.IntegrityError:
            return render_template('register.html', error='Username or email already exists')
        
    # Get flashed messages for template
    error = get_flashed_messages(category_filter=['error'])
    success = get_flashed_messages(category_filter=['success'])
    
    return render_template('register.html', 
                         error=error[0] if error else None,
                         success=success[0] if success else None)

# Login decorator
def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = db.get_user_by_username(username)
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            return redirect(url_for('index'))
        
        return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/video/<int:video_id>/comment', methods=['POST'])
@login_required
def add_comment(video_id):
    if not db.can_user_comment(session['user_id']):
        flash('You can only post one comment per 5 min.', 'error')
        return redirect(url_for('video_details', video_id=video_id))  # Updated to match route name
        
    content = request.form.get('content', '').strip()
    if not content:
        flash('Comment cannot be empty.', 'error')
        return redirect(url_for('video_details', video_id=video_id))  # Updated to match route name
        
    db.add_comment(session['user_id'], video_id, content)
    return redirect(url_for('video_details', video_id=video_id))  # Updated to match route name

@app.route('/feed.xml')
def rss_feed():
    """Generate RSS feed of latest videos."""
    fg = FeedGenerator()
    fg.title('Cobra DB Video Feed')
    fg.description('Latest videos from Cobra DB')
    fg.link(href=request.url_root)
    fg.language('en')
    
    # Get latest videos (maybe last 20)
    videos = db.get_all_videos(page=1, per_page=20)['videos']
    
    for video in videos:
        fe = fg.add_entry()
        fe.title(video['title'])
        fe.link(href=f"{request.url_root}video/{video['id']}")
        
        # Build content with video details
        content = f"""
        <p>{video['summary'] if video['summary'] else ''}</p>
        <p>Channel: {video['channel_name']}</p>
        <p>Posted: {video['youtube_created_at']}</p>
        """
        if video['thumbnail_url']:
            content = f"<img src='{video['thumbnail_url']}' alt='{video['title']}'><br>" + content
            
        fe.content(content, type='html')
        fe.published(datetime.fromisoformat(video['youtube_created_at'].replace('Z', '+00:00')))
        
    response = make_response(fg.rss_str())
    response.headers.set('Content-Type', 'application/rss+xml')
    return response

@app.context_processor
def inject_user():
    """Inject user info into templates."""
    if 'user_id' in session:
        user = db.get_user_by_id(session['user_id'])
        return dict(user=user)
    return dict()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9595, debug=True)