from flask import Flask, render_template, request, jsonify
from database import DatabaseManager
import markdown
import re

app = Flask(__name__)
db = DatabaseManager('db.sqlite')

@app.template_filter('markdown')
def markdown_filter(text):
    if not text:
        return ""
    return markdown.markdown(text)

@app.template_filter('nl2br')
def nl2br(text):
    """Convert newlines to HTML line breaks."""
    if not text:
        return ""
    return text.replace('\n', '<br>')

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    videos = db.get_all_videos(page=page)
    return render_template('index.html', videos=videos)

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
    results = db.search_videos(query, page=page)
    return render_template('search.html', results=results, query=query)

@app.route('/topic/<topic_name>')
def topic_videos(topic_name):
    print(f"Route called with topic: {topic_name}")  # Debug log
    page = request.args.get('page', 1, type=int)
    topic_id = db.get_topic_id(topic_name)
    
    print(f"Got topic_id: {topic_id}")  # Debug log
    
    if topic_id is None:
        return "Topic not found", 404
        
    videos = db.get_videos_by_topic(topic_id, page=page)
    print(f"Found {len(videos)} videos for topic")  # Debug log
    return render_template('topic.html', videos=videos, topic=topic_name)

if __name__ == '__main__':
    app.run(debug=True)