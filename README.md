# 📝 Recap - iMessage Chat Summarizer

Automatically summarize iMessage conversations using Gemini AI. Just type `@recap` in any chat and get an instant AI-generated summary sent right back to you.

## 🚀 Usage

Once set up, using Recap is simple:

### In any iMessage conversation:

**Basic usage:**
```
@recap
```
Gets a summary of the last 60 messages

**Custom message count:**
```
@recap 100
```
Summarizes the last 100 messages (range: 10-500)

The bot will:
1. ✅ Detect your @recap mention
2. 📚 Fetch the requested number of recent messages  
3. 🤖 Generate an AI summary using Gemini
4. 💬 Send the summary back to the chat automatically

**Example output:**
```
📝 Chat Recap:

The conversation centered around coordinating study plans for the upcoming EECS 281 
midterm. Multiple participants expressed concerns about the difficulty of priority queue free response problems. One member suggested forming a study group at "the UGLI" tomorrow at 6 PM, but another pointed out that because it's a Friday, they would have to take "Commuter North" to "The Dude".
```

### Service Management

The monitor runs automatically in the background when your Mac is on. To manage it:

```bash
./service.sh status    # Check if running
./service.sh logs      # View live logs
./service.sh restart   # Restart (after code changes)
./service.sh stop      # Stop temporarily
./service.sh start     # Start again
```

---

## 🛠️ Setup Guide

### Prerequisites

**System Requirements:**
- macOS (any version with Messages app)
- Python 3.8 or higher
- 50MB free disk space

**API Requirements:**
- Google Gemini API key(s) - **100% FREE** (no credit card needed)
- Get your first key: https://aistudio.google.com/app/apikey
- Optional: Create multiple Google Cloud Projects for higher rate limits (see Advanced Configuration)

### Step 1: Clone and Navigate

```bash
cd ~/Documents  # or wherever you want to install
git clone <your-repo-url> text-ai
cd text-ai
```

### Step 2: Run Setup Script

```bash
./setup.sh
```

This will:
- Create a Python virtual environment
- Install all required packages (google-genai, python-dotenv, etc.)
- Clean up conflicting dependencies

### Step 3: Configure API Keys

Create a `.env` file in the project directory:

```bash
nano .env
```

Add your Gemini API key(s):
```env
# Single key (most users)
GEMINI_API_KEY=your_api_key_here

# Multiple keys (one per Google Cloud Project for higher rate limits)
GEMINI_API_KEY_1=your_first_key
GEMINI_API_KEY_2=your_second_key
GEMINI_API_KEY_3=your_third_key
```

**🎓 Tip:** Gemini API is free for everyone. One key is usually enough, but if you hit rate limits, create multiple Google Cloud Projects (not just keys) and add one key per project. Rate limits are per project, not per key.

Save and exit (`Ctrl+X`, then `Y`, then `Enter`)

### Step 4: Grant Permissions

**Critical:** macOS requires explicit permission to access the Messages database.

#### 4a. Grant Full Disk Access to Python

1. Open **System Settings** (or System Preferences on older macOS)
2. Go to **Privacy & Security** → **Full Disk Access**
3. Click the **🔒 lock** icon and authenticate
4. Click the **+** button
5. Press **`Cmd+Shift+G`** to open "Go to folder"
6. Paste the path to your Python binary (replace `YOUR_USERNAME` and adjust the path if you cloned elsewhere):
   ```
   /Users/YOUR_USERNAME/Documents/text-ai/.venv/bin/python3
   ```
7. Click **Open**
8. Ensure the toggle next to python3 is **ON** (blue)

#### 4b. Grant Automation Access to Terminal (if prompted)

When you first run the service, macOS may ask:
- "Terminal would like to control Messages.app"
- Click **OK** or **Allow**

### Step 5: Install the Service

Make the service script executable and install:

```bash
chmod +x service.sh
./service.sh install
```

You should see:
```
📦 Installing Recap Monitor service...
✅ Service installed and started
   Will auto-start on login/boot
```

### Step 6: Verify Installation

Check that everything is working:

```bash
./service.sh status
```

Expected output:
```
✅ Recap Monitor is running

📋 Recent logs:
🤖 Recap Monitor Starting...
   Watching for @recap mentions in iMessage

🔑 Loaded 1 API key(s)
📍 Monitoring started (message ID: 456701)
   Press Ctrl+C to stop
```

If you see errors about "unable to open database file", review Step 4 above.

### Step 7: Test It Out

1. Open Messages app
2. Send yourself a test message: `@recap`
3. Wait 2-5 seconds
4. You should receive an automated recap!

Check logs in real-time:
```bash
./service.sh logs
```

---

## 📁 Project Structure

```
text-ai/
├── recap_monitor.py         # Main monitoring script
├── service.sh               # Service management tool (generates plist)
├── setup.sh                 # Installation script
├── requirements.txt         # Python dependencies
├── .env                     # Your API keys (gitignored)
├── .gitignore              # Git exclusions
├── recap_monitor.log        # Service logs (generated)
└── README.md               # This file
```

**Note:** The LaunchAgent configuration (`com.recap.monitor.plist`) is automatically generated by `service.sh` during installation with the correct paths for your system.

---

## 🔧 Advanced Configuration

### Adjusting Message Count Limits

Edit `recap_monitor.py`, find `parse_recap_limit()`:

```python
return min(max(limit, 10), 500)  # Change 500 to your max
```

### Changing Poll Interval

Edit `recap_monitor.py`, find `time.sleep(2)`:

```python
time.sleep(2)  # Change to 5 for less frequent checks
```

### Multiple API Keys for Higher Capacity

To increase rate limits, create multiple Google Cloud Projects and add one key per project:

```env
GEMINI_API_KEY_1=key_from_project_one
GEMINI_API_KEY_2=key_from_project_two
```

The bot automatically rotates to the next key when one hits its limit. Create projects at https://console.cloud.google.com/projectcreate

---

## 🐛 Troubleshooting

### Service won't start

**Check logs:**
```bash
./service.sh logs
```

**Common issues:**
- ❌ "unable to open database file" → Grant Full Disk Access (Step 4a)
- ❌ "No API keys found" → Check your `.env` file (Step 3)
- ❌ "ImportError: No module named google" → Run `./setup.sh` again

### Bot not responding to @recap

1. **Verify service is running:**
   ```bash
   ./service.sh status
   ```

2. **Check recent logs:**
   ```bash
   tail -20 recap_monitor.log
   ```

3. **Test manually:**
   ```bash
   source .venv/bin/activate
   python3 recap_monitor.py
   ```
   Then send `@recap` and watch the terminal output

### Service doesn't start on boot

Re-install the service:
```bash
./service.sh uninstall
./service.sh install
```

---

## 🔒 Security & Privacy

- **Local Processing:** All message data stays on your Mac
- **API Calls:** Only message text is sent to Google Gemini API
- **No Storage:** Messages aren't stored, only read temporarily
- **API Keys:** Stored in `.env` (never committed to git)

**Database Access:** The script has read-only access to your Messages database at `~/Library/Messages/chat.db`

---

## ⚡ Performance

**Battery Impact:** ~0.1-0.3W (negligible - less than a browser tab)

**CPU Usage:** ~0-0.1% idle, ~5-10% when generating summaries

**Network:** Only when @recap is triggered (~1-50KB per request)

**Startup Time:** Instant if already running, ~2 seconds for first launch

---

## 🎯 How It Works

1. **Database Monitoring:** Polls Messages DB every 2 seconds for new messages
2. **Mention Detection:** Looks for "@recap" in message text
3. **Message Fetching:** Extracts recent conversation history
4. **AI Processing:** Sends to Gemini with context-aware prompt
5. **Response Sending:** Uses AppleScript to send summary back

**Technical Stack:**
- Python 3.12
- google-genai SDK
- SQLite3 (for Messages DB access)
- AppleScript (for sending messages)
- macOS LaunchAgent (for auto-start)

---

## 📝 License

MIT

---