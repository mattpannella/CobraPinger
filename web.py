from flask import Flask, render_template, request, jsonify
from database import DatabaseManager
import markdown
import re
from datetime import datetime
import calendar

app = Flask(__name__, static_folder='static')

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
    page = request.args.get('page', 1, type=int)
    selected_channels = request.args.getlist('channels', type=int)
    
    channels = db.get_all_channels()
    result = db.get_all_videos(
        page=page, 
        channel_ids=selected_channels if selected_channels else None
    )
    
    # Get random quote
    quote = db.get_random_quote()
    
    return render_template(
        'index.html', 
        videos=result['videos'],
        total=result['total'],
        pages=result['pages'],
        current_page=page,
        channels=channels,
        selected_channels=selected_channels,
        quote=quote
    )

@app.route('/video/<int:video_id>')
def video_detail(video_id):
    video = db.get_video_details(video_id)
    if video:
        return render_template('video.html', video=video)
    return "Video not found", 404

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
    
    return render_template(
        'calendar.html',
        calendar=cal,
        video_map=video_map,
        month=month,
        month_name=month_name,
        year=year,
        prev_month=prev_month,
        prev_year=prev_year,
        next_month=next_month,
        next_year=next_year
    )

@app.route('/topics')
def topic_cloud():
    """Show all topics in a tag cloud."""
    topics = db.get_topic_counts()  # We'll create this method
    return render_template('topics.html', topics=topics)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9595, debug=True)