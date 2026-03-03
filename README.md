# 🤖 Grok - iMessage Chat Summarizer

Automatically summarize iMessage conversations using Gemini AI. Just mention `@grok` in any group chat and get an instant summary!

## Features

- 📱 **Interactive Summarizer**: Manually summarize any chat conversation
- 🔄 **Auto-Monitor Mode**: Watch for `@grok` mentions and auto-respond with summaries
- 🧠 **Powered by Gemini**: Uses Google's Gemini AI for intelligent summaries
- 💬 **iMessage Integration**: Reads from and sends to the iMessage database

## Setup

### 1. Prerequisites

- macOS (required for iMessage access)
- Python 3.12+
- Terminal with **Full Disk Access** (System Settings → Privacy & Security → Full Disk Access)

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure API Key

Create a `.env` file with your Gemini API key:

```bash
cp .env.example .env
# Edit .env and add your actual API key
```

Get your API key from: https://makersuite.google.com/app/apikey

## Usage

### Manual Mode (Interactive)

Summarize any chat conversation:

```bash
python3 summarize_chat.py
```

1. Select a chat from the list
2. Choose how many recent messages to summarize
3. Get an AI-generated summary

### Auto-Monitor Mode (@grok)

Watch for `@grok` mentions and auto-respond:

```bash
python3 grok_monitor.py
```

Now in any group chat, just type `@grok` and the bot will:
1. Detect the mention
2. Fetch recent messages (default: 60)
3. Generate a summary
4. Send it back to the chat

**Flexible Message Limit:**
- `@grok` - Summarize last 60 messages (default)
- `@grok 100` - Summarize last 100 messages
- `@grok 300` - Summarize last 300 messages
- Range: 10-1000 messages

**Note**: For group chats, the monitor will print the summary for you to copy/paste manually (Apple restricts sending to group chats programmatically).

## Files

- `summarize_chat.py` - Interactive chat summarizer
- `grok_monitor.py` - Auto-monitoring daemon for @grok mentions
- `test_db.py` - Database connectivity tester
- `send_imessage.sh` - Helper script to send iMessages via AppleScript
- `.env` - Your API key configuration (not tracked in git)

## How It Works

1. **Database Access**: Reads from `~/Library/Messages/chat.db` (iMessage database)
2. **Message Extraction**: Handles both plain text and `attributedBody` fields
3. **AI Summarization**: Sends conversation to Gemini for intelligent summary
4. **Response**: Displays or sends the summary back

## Troubleshooting

### "Database not found"
- Make sure Messages app has been used on this Mac
- Grant Terminal Full Disk Access in System Settings

### "No messages found"
- Some system messages don't have text content
- Try a different chat with actual text messages

### "Failed to send message"
- For group chats, AppleScript has limitations
- Copy the generated summary and paste manually
- Works fine for individual chats

## Development

### Test Database Connection
```bash
python3 test_db.py
```

### Debug Mode
The scripts print debug info showing:
- Messages found
- Text extraction status
- API calls

## Future Ideas

- [ ] Better group chat sending support
- [ ] Custom summary styles/formats
- [ ] Message filtering (date ranges, keywords)
- [ ] Multiple AI model support
- [ ] Web dashboard for managing summaries

## License

MIT