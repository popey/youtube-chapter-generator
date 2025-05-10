#!/usr/bin/env python3
"""
YouTube Chapter Generator

This script generates chapter markers for YouTube videos using Google's Generative AI.
It downloads video metadata and subtitles using yt-dlp and then uses Google's AI to 
generate appropriate chapter markers.

Usage:
    python youtube_chapter_generator.py <youtube_url> [--model MODEL]

Arguments:
    youtube_url      URL of the YouTube video
    --model MODEL    Optional: Override the default AI model
                     Choices: gemini-2.5-pro-exp, gemini-2.5-flash, gemini-1.5-pro
"""

import os
import sys
import argparse
import subprocess
import json
import re
import urllib.parse
import google.generativeai as genai
from pathlib import Path
from dotenv import load_dotenv
import textwrap
import logging

# Load environment variables from .env file
load_dotenv()

# Default model to use
DEFAULT_MODEL = "gemini-2.5-flash"

# Models map for command line arguments
# gemini-2.5-flash-preview-04-17 supports code execution,
# function calling, search groubnding, structured outputs, and thinking
# Input token limit: 1,048,576
# Output token limit: 65,536
MODELS = {
    "gemini-2.5-pro-exp": "models/gemini-2.5-pro-exp-03-25",
    "gemini-2.5-flash": "models/gemini-2.5-flash-preview-04-17"
}

# Configure logging
logging.basicConfig(
    filename="youtube_chapter_generator.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate chapter markers for YouTube videos")
    parser.add_argument("url", help="URL of the YouTube video")
    parser.add_argument("--model", choices=list(MODELS.keys()), 
                        default=DEFAULT_MODEL, 
                        help="AI model to use for generation")
    parser.add_argument("--prompt", help="Path to a text file containing the prompt")
    return parser.parse_args()

def run_ytdlp_command(url, command_args):
    """Run yt-dlp command and return the output."""
    try:
        cmd = ["yt-dlp", "--skip-download"] + command_args + [url]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        print(f"Error running yt-dlp command: {e}")
        print(f"Command output: {e.stderr}")
        return None, e.stderr

def extract_github_urls_from_livechat(livechat_file):
    """
    Extract GitHub URLs from live chat JSON file with their timestamps.
    
    This function parses the live chat JSON file, finds GitHub URLs in the messages,
    extracts the clean GitHub URLs without tracking parameters, and organizes them
    by their timestamps in the video.
    
    Args:
        livechat_file: Path to the live chat JSON file
        
    Returns:
        A list of dictionaries containing timestamp and clean GitHub URL
    """
    if not livechat_file or not livechat_file.exists():
        return []
    
    github_urls = []
    
    try:
        # Read the JSON file line by line since it might not be a valid JSON array
        with open(livechat_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    # Try to parse each line as a JSON object
                    chat_item = json.loads(line)
                    
                    # Look for the replay chat item actions
                    if "replayChatItemAction" in chat_item:
                        actions = chat_item["replayChatItemAction"]["actions"]
                        for action in actions:
                            if "addChatItemAction" in action:
                                item = action["addChatItemAction"]["item"]
                                if "liveChatTextMessageRenderer" in item:
                                    renderer = item["liveChatTextMessageRenderer"]
                                    
                                    # Get the timestamp
                                    timestamp = renderer.get("timestampText", {}).get("simpleText", "")
                                    
                                    # Get the message content
                                    if "message" in renderer and "runs" in renderer["message"]:
                                        runs = renderer["message"]["runs"]
                                        for run in runs:
                                            if "navigationEndpoint" in run and "urlEndpoint" in run["navigationEndpoint"]:
                                                url_info = run["navigationEndpoint"]["urlEndpoint"]
                                                if "url" in url_info:
                                                    raw_url = url_info["url"]
                                                    
                                                    # Extract the actual GitHub URL from the tracking URL
                                                    if "q=" in raw_url:
                                                        parsed_url = urllib.parse.urlparse(raw_url)
                                                        query_params = urllib.parse.parse_qs(parsed_url.query)
                                                        if "q" in query_params:
                                                            actual_url = query_params["q"][0]
                                                            
                                                            # Check if it's a GitHub URL
                                                            if "github.com/" in actual_url:
                                                                github_urls.append({
                                                                    "timestamp": timestamp,
                                                                    "url": actual_url
                                                                })
                                                    elif "github.com/" in raw_url:
                                                        # Direct GitHub URL without tracking
                                                        github_urls.append({
                                                            "timestamp": timestamp,
                                                            "url": raw_url
                                                        })
                except json.JSONDecodeError:
                    # Skip lines that aren't valid JSON
                    continue
                except Exception as e:
                    print(f"Error processing live chat line: {e}")
                    continue
        
        print(f"Found {len(github_urls)} GitHub URLs in live chat")
        return github_urls
    
    except Exception as e:
        print(f"Error processing live chat file: {e}")
        return []

def get_video_info(url):
    """Get video title, description, subtitles, and live chat if available."""
    logging.info("Retrieving video metadata...")
    print("Retrieving video metadata...")
    
    # Get video info (title, description, etc.)
    info_args = ["--dump-json"]
    info_stdout, info_stderr = run_ytdlp_command(url, info_args)
    
    if not info_stdout:
        logging.error("Failed to retrieve video information.")
        print("Failed to retrieve video information.")
        sys.exit(1)
    
    video_info = json.loads(info_stdout)
    video_id = video_info.get('id', 'unknown')
    title = video_info.get('title', 'Unknown Title')
    description = video_info.get('description', '')
    
    logging.debug(f"Video title: {title}")
    logging.debug(f"Video ID: {video_id}")
    logging.debug(f"Description: {description}")
    
    print(f"Video title: {title}")
    print(f"Video ID: {video_id}")
    
    # Get English subtitles
    subtitle_args = ["--write-sub", "--write-auto-sub", "--sub-lang", "en", "--convert-subs", "srt"]
    logging.info("Downloading English subtitles...")
    print("Downloading English subtitles...")
    sub_stdout, sub_stderr = run_ytdlp_command(url, subtitle_args)
    
    # Try to get live chat if available
    livechat_args = ["--write-sub", "--sub-lang", "live_chat"]
    logging.info("Attempting to download live chat (if available)...")
    print("Attempting to download live chat (if available)...")
    chat_stdout, chat_stderr = run_ytdlp_command(url, livechat_args)
    
    # Find the generated subtitle files
    subtitle_file = None
    livechat_file = None
    
    # List all files in current directory for debugging
    logging.info("Looking for subtitle and live chat files...")
    print("Looking for subtitle and live chat files...")
    all_files = list(Path('.').glob('*'))
    logging.debug(f"Found {len(all_files)} files in directory")
    print(f"Found {len(all_files)} files in directory")
    
    # Store already processed files to avoid duplicates
    processed_files = set()
    
    # Look for subtitle files with more flexible patterns
    subtitle_patterns = [
        f"{video_id}*.srt",           # Standard ID-based naming
        f"{video_id}*.vtt",           # VTT format
        f"*{video_id}*.srt",          # ID anywhere in filename
        f"*{video_id}*.vtt",          # ID anywhere in filename
        f"*{video_id}*.json",         # JSON format
        f"*[{video_id}]*.srt",        # ID in brackets
        f"*[{video_id}]*.vtt",        # ID in brackets
        f"*[{video_id}]*.en.srt",     # ID in brackets with language
        f"*[{video_id}]*en.srt",      # ID in brackets with language
    ]
    
    for pattern in subtitle_patterns:
        matching_files = list(Path('.').glob(pattern))
        for file in matching_files:
            # Skip if we've already processed this file
            if str(file) in processed_files:
                continue
                
            # Make sure the file actually contains the video ID (as a stronger check)
            if video_id not in file.name:
                continue
                
            processed_files.add(str(file))
            logging.debug(f"Found potential subtitle file: {file}")
            print(f"Found potential subtitle file: {file}")
            
            if "live_chat" in file.name.lower():
                if not livechat_file:  # Only set if not already found
                    livechat_file = file
            else:
                if not subtitle_file:  # Only set if not already found
                    subtitle_file = file
    
    # Read subtitle content
    subtitle_content = ""
    if subtitle_file:
        logging.info(f"Using subtitle file: {subtitle_file}")
        print(f"Using subtitle file: {subtitle_file}")
        subtitle_content = subtitle_file.read_text(encoding='utf-8', errors='replace')
    else:
        logging.warning("No subtitle file found.")
        print("No subtitle file found.")
    
    # Read live chat content
    livechat_content = ""
    github_urls = []
    if livechat_file:
        logging.info(f"Using live chat file: {livechat_file}")
        print(f"Using live chat file: {livechat_file}")
        
        # Check if it's a JSON file for processing GitHub URLs
        if livechat_file.name.endswith('.json'):
            # Extract GitHub URLs from the live chat JSON
            github_urls = extract_github_urls_from_livechat(livechat_file)
            
            # Also read the raw content for backup
            livechat_content = livechat_file.read_text(encoding='utf-8', errors='replace')
        else:
            livechat_content = livechat_file.read_text(encoding='utf-8', errors='replace')
    else:
        logging.warning("No live chat file found.")
        print("No live chat file found.")
    
    # Check if we have either subtitles or live chat
    if not subtitle_content and not livechat_content:
        logging.error("Neither subtitles nor live chat could be retrieved.")
        print("Error: Neither subtitles nor live chat could be retrieved.")
        print("At least one of these is required to generate chapter markers.")
        sys.exit(1)
    
    return {
        "title": title,
        "description": description,
        "subtitles": subtitle_content,
        "live_chat": livechat_content,
        "github_urls": github_urls,
        "video_id": video_id
    }

def parse_srt_to_text(srt_content):
    """Convert SRT subtitle format to plain text."""
    # Remove SRT formatting (timestamps and numbering)
    lines = srt_content.split('\n')
    cleaned_lines = []
    
    i = 0
    while i < len(lines):
        # Skip subtitle numbers
        if lines[i].strip().isdigit():
            i += 1
            # Skip timestamp line
            if i < len(lines):
                i += 1
            # Collect text until empty line or end
            text_segment = []
            while i < len(lines) and lines[i].strip():
                text_segment.append(lines[i])
                i += 1
            if text_segment:
                cleaned_lines.append(" ".join(text_segment))
        else:
            i += 1
    
    return " ".join(cleaned_lines)

default_prompt = textwrap.dedent("""
Your goal is to create a block of text in YouTube chapter format only.

User provides:
* Description from a youtube video
* Live chat log from the video (if available)
* Transcript from the video

Please create a list of timestamps in youtube description format that I can paste directly in the youtube video description to generate the chapter markers. It should list the time we start talking about something and a concise but descriptive topic name.

Follow these guidelines:
* Format each line exactly as: `[timestamp] [chapter title]` (e.g., "0:00 Introduction")
* Include 5-10 chapters depending on video length (more chapters for longer videos)
* Focus on major topic changes, demos, segments, or guest introductions
* Make chapter titles descriptive but concise (2-5 words is ideal)
* Start with a chapter at 0:00 (required by YouTube)
* Do not use backticks or other formatting in your response
* Do not include any explanatory text before or after the chapter markers

Suggest three hashtags for the end of the description, appropriate for the video content.
""")

def parse_prompt_file(prompt_file):
    """Read the prompt from a file."""
    try:
        with open(prompt_file, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading prompt file {prompt_file}: {e}")
        sys.exit(1)

def generate_chapters(video_info, model_name, prompt_text):
    """Generate chapter markers using Google's Generative AI."""
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        logging.error("GOOGLE_API_KEY environment variable not set.")
        print("Error: GOOGLE_API_KEY environment variable not set.")
        print("Please set this variable in a .env file or export it in your shell.")
        sys.exit(1)

    # Configure the Google Generative AI API
    genai.configure(api_key=api_key)

    # Select the model
    model = genai.GenerativeModel(model_name)

    # Prepare transcript text
    transcript_text = parse_srt_to_text(video_info["subtitles"])

    # Format the GitHub URLs for inclusion in the prompt
    github_urls_text = ""
    if video_info["github_urls"]:
        github_urls_text = "\n\nGitHub URLs from live chat (with timestamps):\n"
        for item in video_info["github_urls"]:
            github_urls_text += f"{item['timestamp']} - {item['url']}\n"

    # Create the prompt
    prompt = textwrap.dedent(f"""
    {prompt_text}

    VIDEO DESCRIPTION:
    {video_info["description"]}

    TRANSCRIPT:
    {transcript_text[:100000]}

    {github_urls_text}

    LIVE CHAT (if available):
    {video_info["live_chat"][:10000]}
    """)

    logging.debug("Generated prompt for LLM:")
    logging.debug(prompt)

    print("\nGenerating chapter markers...")
    print(f"Using model: {model_name}")

    # Generate content with error handling
    try:
        response = model.generate_content(prompt)
        logging.debug("Response from LLM:")
        logging.debug(response.text)
        return response.text
    except Exception as e:
        logging.error("Google Gemini API call failed:", exc_info=True)
        print("\nError: Google Gemini API call failed:")
        print(f"{str(e)}")
        print("\nPossible causes:")
        print("- Invalid API key")
        print("- Invalid model name or model not available")
        print("- Rate limit or quota exceeded")
        print("- Network connectivity issues")
        print("\nPlease check your API key and model availability.")
        sys.exit(1)

def main():
    """Main function to run the program."""
    args = parse_arguments()
    
    # Map the short model name to the full model name
    model_name = MODELS.get(args.model, DEFAULT_MODEL)
    
    # Get video information
    video_info = get_video_info(args.url)
    
    # If we found GitHub URLs in the live chat, save them to a file too
    if video_info["github_urls"]:
        github_urls_file = f"{video_info['video_id']}_github_urls.txt"
        with open(github_urls_file, "w", encoding="utf-8") as f:
            f.write("GitHub URLs extracted from live chat:\n\n")
            for item in video_info["github_urls"]:
                f.write(f"{item['timestamp']} - {item['url']}\n")
        print(f"\nExtracted GitHub URLs saved to {github_urls_file}")
    
    # Parse the prompt
    if args.prompt:
        prompt_text = parse_prompt_file(args.prompt)
    else:
        prompt_text = default_prompt
    
    # Generate chapter markers
    chapters = generate_chapters(video_info, model_name, prompt_text)
    
    # Save the generated chapters to a file
    output_file = f"{video_info['video_id']}_chapters.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(chapters)
    
    print(f"\nChapter markers generated and saved to {output_file}")
    print("\nGenerated Chapter Markers:")
    print("===========================")
    print(chapters)
    print("===========================")
    
    print(f"\nYou can copy these timestamps directly into your YouTube video description.")

if __name__ == "__main__":
    main()