#!/usr/bin/env python3
"""
Chat Summarizer using Gemini
Fetches messages from iMessage database and generates summaries
"""

import sqlite3
import os
from datetime import datetime, timedelta
from google import genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database path
IMESSAGE_DB = os.path.expanduser("~/Library/Messages/chat.db")

def extract_text_from_attributed_body(attributed_body):
    """Extract readable text from attributedBody blob"""
    if not attributed_body:
        return None
    try:
        decoded = attributed_body.decode('utf-8', errors='ignore')
        if 'NSString' in decoded:
            parts = decoded.split('NSString')
            for part in parts[1:]:
                cleaned = ''.join(c for c in part if c.isprintable())
                if len(cleaned) > 2:
                    return cleaned[:200]
    except Exception:
        pass
    return None

def get_chats():
    """Get list of available chats"""
    conn = sqlite3.connect(f"file:{IMESSAGE_DB}?mode=ro", uri=True)
    cursor = conn.cursor()
    
    query = """
    SELECT 
        c.ROWID,
        c.chat_identifier,
        c.display_name,
        COUNT(m.ROWID) as message_count
    FROM chat c
    LEFT JOIN chat_message_join cmj ON c.ROWID = cmj.chat_id
    LEFT JOIN message m ON cmj.message_id = m.ROWID
    GROUP BY c.ROWID
    HAVING message_count > 0
    ORDER BY c.ROWID DESC
    LIMIT 20
    """
    
    cursor.execute(query)
    chats = cursor.fetchall()
    conn.close()
    
    return chats

def get_messages(chat_id, limit=100):
    """Get recent messages from a specific chat"""
    conn = sqlite3.connect(f"file:{IMESSAGE_DB}?mode=ro", uri=True)
    cursor = conn.cursor()
    
    query = """
    SELECT 
        m.text,
        m.attributedBody,
        m.is_from_me,
        m.date,
        h.id as sender_id
    FROM chat_message_join cmj
    JOIN message m ON cmj.message_id = m.ROWID
    LEFT JOIN handle h ON m.handle_id = h.ROWID
    WHERE cmj.chat_id = ?
    ORDER BY m.date DESC
    LIMIT ?
    """
    
    cursor.execute(query, (chat_id, limit))
    messages = cursor.fetchall()
    conn.close()
    
    # Reverse to get chronological order
    messages.reverse()
    
    # Format messages
    formatted_messages = []
    for text, attributed_body, is_from_me, date, sender_id in messages:
        message_text = text or extract_text_from_attributed_body(attributed_body)
        
        if not message_text:
            continue
            
        # Convert Apple timestamp (nanoseconds since 2001-01-01)
        readable_date = datetime(2001, 1, 1) + timedelta(seconds=date/1e9)
        
        sender = "Me" if is_from_me else (sender_id or "Other")
        formatted_messages.append({
            'text': message_text,
            'sender': sender,
            'date': readable_date,
            'is_from_me': is_from_me
        })
    
    return formatted_messages

def summarize_messages(messages, api_key):
    """Use Gemini to summarize messages"""
    os.environ['GOOGLE_API_KEY'] = api_key
    client = genai.Client()
    
    # Build conversation text
    conversation = []
    for msg in messages:
        timestamp = msg['date'].strftime("%Y-%m-%d %H:%M")
        conversation.append(f"[{timestamp}] {msg['sender']}: {msg['text']}")
    
    conversation_text = "\n".join(conversation)
    
    prompt = f"""Please summarize the following text conversation. 
Focus on:
- Main topics discussed
- Important decisions or plans
- Action items or next steps
- Overall tone/sentiment

Conversation:
{conversation_text}

Provide a concise summary:"""
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text

def main():
    print("🤖 Chat Summarizer with Gemini\n")
    
    # Check database access
    if not os.path.exists(IMESSAGE_DB):
        print(f"❌ Database not found at: {IMESSAGE_DB}")
        print("Make sure Terminal has Full Disk Access")
        return
    
    # Get Gemini API key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY environment variable not set")
        print("Set it with: export GEMINI_API_KEY='your-key-here'")
        return
    
    # List available chats
    print("📱 Available chats:\n")
    chats = get_chats()
    
    for rowid, identifier, display_name, msg_count in chats:
        name = display_name or identifier or "Unknown"
        print(f"  {rowid}: {name[:50]} ({msg_count} messages)")
    
    # Get chat selection
    print("\n")
    chat_id = input("Enter chat ID to summarize: ").strip()
    
    try:
        chat_id = int(chat_id)
    except ValueError:
        print("❌ Invalid chat ID")
        return
    
    # Get message limit
    limit_input = input("Number of recent messages to summarize (default 100): ").strip()
    limit = int(limit_input) if limit_input else 100
    
    # Fetch messages
    print(f"\n📥 Fetching {limit} messages from chat {chat_id}...")
    messages = get_messages(chat_id, limit)
    
    if not messages:
        print("❌ No messages found for this chat")
        return
    
    print(f"✅ Found {len(messages)} messages")
    print(f"   Date range: {messages[0]['date'].strftime('%Y-%m-%d')} to {messages[-1]['date'].strftime('%Y-%m-%d')}")
    
    # Generate summary
    print("\n🤔 Generating summary with Gemini...")
    summary = summarize_messages(messages, api_key)
    
    print("\n" + "="*80)
    print("📝 SUMMARY")
    print("="*80)
    print(summary)
    print("="*80)

if __name__ == "__main__":
    main()
