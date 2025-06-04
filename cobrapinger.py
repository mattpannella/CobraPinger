import feedparser
import time
import os
import openai
from youtube_transcript_api import YouTubeTranscriptApi, CouldNotRetrieveTranscript
from discord_webhook import DiscordWebhook
import json
import pyfiglet
import sys
import select
import re
import traceback

CONFIG_FILE = "config.json"

def sanitize_filename(filename):
    """Sanitize the filename by removing or replacing invalid characters."""
    return re.sub(r'[\\/*?:"<>|]', "", filename)

def ensure_youtuber_directory(youtuber_name):
    """Ensure a directory exists for the YouTuber, create it if it doesn't."""
    youtuber_directory = os.path.join(os.getcwd(), youtuber_name)
    if not os.path.exists(youtuber_directory):
        os.makedirs(youtuber_directory)
    return youtuber_directory

def load_config():
    """Load the configuration from the JSON file."""
    with open(CONFIG_FILE, "r") as file:
        return json.load(file)

def save_config(config):
    """Save the configuration to the JSON file."""
    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file, indent=4)

def log(message):
    """Print a message to the console with a timestamp."""
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}")

def load_last_video_data(youtuber_name):
    """Load the last processed video data (ID, title, published date) from the file."""
    last_video_file = f"{youtuber_name}_last_video_data.json"
    if os.path.exists(last_video_file):
        with open(last_video_file, "r") as file:
            return json.load(file)
    return []

def save_last_video_data(youtuber_name, video_data):
    """Save the last processed video data (ID, title, published date) to the file."""
    last_video_file = f"{youtuber_name}_last_video_data.json"
    with open(last_video_file, "w") as file:
        json.dump(video_data, file, indent=4)

def save_transcript_to_file(transcript, youtuber_name, video_title, video_published):
    """Save the transcript to a text file in the YouTuber's directory."""
    # Sanitize video title and create the directory
    sanitized_title = sanitize_filename(video_title)
    youtuber_directory = ensure_youtuber_directory(youtuber_name)

    # Format the filename using the video title and published date
    transcript_file = os.path.join(youtuber_directory, f"{sanitized_title} - {video_published}.txt")
    
    log(f"Saving transcript to {transcript_file}...")
    with open(transcript_file, "w", encoding="utf-8") as file:
        file.write(transcript)
    log("Transcript successfully saved.")

def fetch_new_video(rss_feed_url):
    """Fetch the latest video from the RSS feed."""
    log("Checking the RSS feed for new videos...")
    feed = feedparser.parse(rss_feed_url)
    if len(feed.entries) > 0:
        log("New video found in the RSS feed.")
        return feed.entries[0]
    log("No new video found in the RSS feed.")
    return None

def fetch_transcript(video_id):
    """Fetch the transcript for the given video ID."""
    log(f"Attempting to fetch the transcript for video ID: {video_id}")
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        log("Transcript successfully fetched.")
        return " ".join([entry['text'] for entry in transcript])
    except CouldNotRetrieveTranscript:
        log("Transcript could not be retrieved (subtitles may be disabled).")
        return None
    except Exception as e:
        log(f"An error occurred while fetching the transcript for video ID {video_id}.")
        log("An exception occurred:\n%s", traceback.format_exc())
        return None

def summarize_text(text, system_prompt, client):
    """Summarize the given text using OpenAI's GPT model."""
    log("Sending transcript to OpenAI for summarization...")
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Summarize the following YouTube transcript:\n\n{text}"}
            ],
            max_tokens=1500,
            temperature=0.5,
        )
        log("Transcript successfully summarized.")
        return response.choices[0].message.content.strip()
    except Exception as e:
        log(f"Could not summarize text: {e}")
        return None

def send_discord_notification(video_url, summary, discord_webhook_url):
    #if there is no Discord webhook URL, just print the message
    if not discord_webhook_url:
        print("Discord Webhook URL not set. Summary:")
        print(summary)
        return
    
    """Send a notification to Discord with the video URL and summary."""
    log("Sending notification to Discord...")
    message = f"@everyone **New Video:** {video_url}\n\n**Summary:** {summary}"
    webhook = DiscordWebhook(url=discord_webhook_url, content=message)
    response = webhook.execute()
    if response.status_code == 200:
        log("Notification successfully sent to Discord.")
    else:
        log(f"Failed to send notification to Discord. Status code: {response.status_code}")

def run_program_once(config, client):
    """Run the program once."""
    for youtuber in config['youtubers']:
        log(f"Checking for new videos for {youtuber['name']}...")
        last_video_data = load_last_video_data(youtuber['name'])
        new_video = fetch_new_video(f"https://www.youtube.com/feeds/videos.xml?channel_id={youtuber['channel_id']}")
        if new_video:
            video_id = new_video.yt_videoid
            video_title = new_video.title
            video_published = new_video.published

            if not any(video['id'] == video_id for video in last_video_data):
                log(f"New video detected with ID: {video_id}")
                transcript = fetch_transcript(video_id)
                if transcript:
                    save_transcript_to_file(transcript, youtuber['name'], video_title, video_published)
                    
                    # Check if OpenAI is enabled for this YouTuber
                    if youtuber.get('openai_enabled', True):
                        summary = summarize_text(transcript, youtuber['system_prompt'], client)
                        if not summary:
                            summary = "No summary available."
                    else:
                        summary = "OpenAI functionality is disabled for this YouTuber."

                else:
                   summary = "No transcript found."

                send_discord_notification(new_video.link, summary, config['discord_webhook_url'])

                last_video_data.append({
                    'id': video_id,
                    'title': video_title,
                    'published': video_published
                })
                if len(last_video_data) > 5:  # Keep only the last 5 videos
                    last_video_data.pop(0)

                save_last_video_data(youtuber['name'], last_video_data)
            else:
                log(f"No new video detected for {youtuber['name']}.")

def run_program_continuously(config, client):
    """Run the program continuously, checking for new videos periodically."""
    while True:
        run_program_once(config, client)
        log("Sleeping for 1 minute before checking again...")

        # Wait for 60 seconds in small intervals to allow for early exit
        for _ in range(60):
            time.sleep(1)
            # Check if the user has pressed Enter to break the loop
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                user_input = input()
                if user_input == "":
                    return  # Exit the loop and return to the main menu
                

def list_youtubers(config):
    """List all the YouTubers being tracked."""
    if config['youtubers']:
        log("YouTubers being tracked:")
        for youtuber in config['youtubers']:
            log(f"- {youtuber['name']} (Channel ID: {youtuber['channel_id']})")
    else:
        log("No YouTubers are being tracked currently.")

def add_youtuber(config):
    """Add a new YouTuber to the config."""
    name = input("Enter the YouTuber's name: ")
    channel_id = input("Enter the YouTube Channel ID: ")
    system_prompt = input("Enter the System Agent Prompt: ")

    config['youtubers'].append({
        "name": name,
        "channel_id": channel_id,
        "system_prompt": system_prompt
    })

    save_config(config)
    log(f"YouTuber {name} added successfully.")

def remove_youtuber(config):
    """Remove a YouTuber from the config."""
    if not config['youtubers']:
        log("No YouTubers are being tracked currently.")
        return
    
    print("\n--- Remove YouTuber ---")
    for index, youtuber in enumerate(config['youtubers'], start=1):
        print(f"{index}. {youtuber['name']} (Channel ID: {youtuber['channel_id']})")
    
    print(f"{len(config['youtubers']) + 1}. Cancel")
    
    try:
        choice = int(input("Enter the number of the YouTuber to remove: "))
        if choice == len(config['youtubers']) + 1:
            log("Canceling removal.")
        return

        if 1 <= choice <= len(config['youtubers']):
            youtuber_to_remove = config['youtubers'][choice - 1]
            confirm = input(f"Are you sure you want to remove {youtuber_to_remove['name']}? (y/n): ").lower()
            if confirm == 'y':
                config['youtubers'].pop(choice - 1)
                save_config(config)
                log(f"YouTuber {youtuber_to_remove['name']} removed successfully.")
            else:
                log("Removal canceled.")
        else:
            print("Invalid choice. Please try again.")
    except ValueError:
        print("Invalid input. Please enter a number.")

# Add this function to enable/disable OpenAI for a specific YouTuber
def toggle_openai_for_youtuber(config):
    """Enable or disable OpenAI functionality for a specific YouTuber."""
    if not config['youtubers']:
        log("No YouTubers are being tracked currently.")
        return

    print("\n--- Toggle OpenAI Summarization ---")
    for index, youtuber in enumerate(config['youtubers'], start=1):
        status = "Enabled" if youtuber.get('openai_enabled', True) else "Disabled"
        print(f"{index}. {youtuber['name']} (OpenAI: {status})")

    print(f"{len(config['youtubers']) + 1}. Cancel")

    try:
        choice = int(input("Enter the number of the YouTuber to toggle OpenAI: "))
        if choice == len(config['youtubers']) + 1:
            log("Canceling toggle.")
            return

        if 1 <= choice <= len(config['youtubers']):
            youtuber_to_toggle = config['youtubers'][choice - 1]
            current_status = youtuber_to_toggle.get('openai_enabled', True)
            youtuber_to_toggle['openai_enabled'] = not current_status
            status = "enabled" if youtuber_to_toggle['openai_enabled'] else "disabled"
            save_config(config)
            log(f"OpenAI functionality {status} for {youtuber_to_toggle['name']}.")
        else:
            print("Invalid choice. Please try again.")
    except ValueError:
        print("Invalid input. Please enter a number.")

def configure_api_keys(config):
    """Configure API keys."""
    openai_api_key = input("Enter the OpenAI API Key: ")
    discord_webhook_url = input("Enter the Discord Webhook URL: ")

    config['openai_api_key'] = openai_api_key
    config['discord_webhook_url'] = discord_webhook_url

    save_config(config)
    log("API keys configured successfully.")

# Function to display the ASCII art logo
def display_logo():
    """Display the COBRAPINGER logo using ASCII art."""
    ascii_art = pyfiglet.figlet_format("COBRAPINGER", font="slant")
    print(ascii_art)

def show_menu():
    """Show the main menu."""
    config = load_config()
    openai.api_key = config['openai_api_key']

    while True:
    # Display the COBRAPINGER logo each time the menu is shown
        display_logo()
        print("\n--- YouTube Monitor Menu ---")
        print("1. Run Program Once")
        print("2. Run Program Continuously")
        print("3. List YouTubers Being Tracked")
        print("4. Add New YouTuber")
        print("5. Remove YouTuber")
        print("6. Toggle OpenAI Summarization for a YouTuber")  # New menu option
        print("7. Configure API Keys")
        print("8. Exit")
        choice = input("Enter your choice: ")

        if choice == "1":
            run_program_once(config, openai)
        elif choice == "2":
            run_program_continuously(config, openai)
        elif choice == "3":
            list_youtubers(config)
        elif choice == "4":
            add_youtuber(config)
        elif choice == "5":
            remove_youtuber(config)
        elif choice == "6":
            toggle_openai_for_youtuber(config)  # New function call
        elif choice == "7":
            configure_api_keys(config)
        elif choice == "8":
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    import sys
    config = load_config()
    openai.api_key = config['openai_api_key']

    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        run_program_continuously(config, openai)
    else:
        show_menu()
                    