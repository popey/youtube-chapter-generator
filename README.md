# YouTube Chapter Generator Setup

Follow these steps to set up and run the YouTube Chapter Generator:

## Prerequisites

- Python 3.8 or higher
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) installed
- A Google Gemini API key with access to Generative AI

## Installation

1. Create a directory for the project and navigate to it:
   ```
   mkdir youtube-chapter-generator
   cd youtube-chapter-generator
   ```

2. Save the script as `youtube_chapter_generator.py` in this directory

3. Create a virtual environment using `venv`:
   ```
   python3 -m venv .venv
   ```

4. Activate the virtual environment:
   - On Windows: `.venv\Scripts\activate`
   - On macOS/Linux: `source .venv/bin/activate`

5. Install the required packages:
   ```
   pip install google-generativeai yt-dlp python-dotenv
   ```

6. Create a `.env` file in the project directory with your [Google API](https://aistudio.google.com/app/apikey) key:
   ```
   GOOGLE_API_KEY=your_google_api_key_here
   ```

## Usage

```
python youtube_chapter_generator.py <youtube_url> [--model MODEL] [--prompt PROMPTFILE]
```

Options:
- `youtube_url`: URL of the YouTube video (required)
- `--model`: Model to use for generation (optional)
  - `gemini-2.5-pro-exp`: Gemini 2.5 Pro Experimental
  - `gemini-2.5-flash`: Gemini 2.5 Flash Preview (default)
- `--prompt`: Custom prompt to guide the chapter generation (optional)

## Examples

```
# Using the default model (Gemini 2.5 Flash Preview)
python youtube_chapter_generator.py https://www.youtube.com/watch?v=dQw4w9WgXcQ

# Using a specific model
python youtube_chapter_generator.py https://www.youtube.com/watch?v=dQw4w9WgXcQ --model gemini-2.5-pro-exp

# Using a custom prompt
python youtube_chapter_generator.py https://www.youtube.com/watch?v=dQw4w9WgXcQ --prompt sample_prompt.txt
```

## Output

The script will:
1. Download video metadata, subtitles, and live chat (if available)
2. Process this information with the Google Generative AI model
3. Generate chapter markers in YouTube format
4. Save the output to `[video_id]_chapters.txt`
5. Display the generated chapters in the terminal

## Sample output

```bash
python youtube_chapter_generator.py https://www.youtube.com/watch\?v\=VqNaOOm7Dhw
Retrieving video metadata...
Video title: NixOS | More Nix ❄️ packaging & fixes 🩹 for OBS Studio 📡
Video ID: VqNaOOm7Dhw
Downloading English subtitles...
Attempting to download live chat (if available)...
Looking for subtitle and live chat files...
Found 8 files in directory
Found potential subtitle file: NixOS ｜ More Nix ❄️ packaging & fixes 🩹 for OBS Studio 📡 [VqNaOOm7Dhw].en.srt
Found potential subtitle file: NixOS ｜ More Nix ❄️ packaging & fixes 🩹 for OBS Studio 📡 [VqNaOOm7Dhw].live_chat.json
Using subtitle file: NixOS ｜ More Nix ❄️ packaging & fixes 🩹 for OBS Studio 📡 [VqNaOOm7Dhw].en.srt
Using live chat file: NixOS ｜ More Nix ❄️ packaging & fixes 🩹 for OBS Studio 📡 [VqNaOOm7Dhw].live_chat.json
Found 0 GitHub URLs in live chat

Generating chapter markers...
Using model: models/gemini-2.5-flash-preview-04-17

Chapter markers generated and saved to VqNaOOm7Dhw_chapters.txt

Generated Chapter Markers:
===========================
00:00 - Intro
04:10 - Stream Start & Recap
05:40 - Fixing OBS Plugin Build Errors (Compiler Warnings)
09:50 - Applying Fix to Multi-Warning Plugin
14:00 - Moving to Native NixOS OBS Config
15:20 - Reviewing OBS Nixpkgs Changes (ALSA)
21:00 - Building OBS with ALSA Disabled
26:45 - Testing the Build
29:10 - Verifying ALSA is Disabled
30:25 - Committing the Change
31:10 - Exploring Alternative AAC Codec

#nixos #obsstudio #linux
===========================

You can copy these timestamps directly into your YouTube video description.
```

## Troubleshooting

- If you see an error about the API key, make sure your `.env` file is properly set up
- If yt-dlp can't find subtitles, the video might not have them available
- If the model seems to produce irrelevant chapters, try a different model using the `--model` parameter
- If neither subtitles nor live chat are available, the script will exit with an error, as at least one is required to generate chapters.
