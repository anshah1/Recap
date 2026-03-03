#!/usr/bin/env python3
"""
Grok Monitor - Watches for @grok mentions in iMessage and auto-responds with summaries
"""

import sqlite3
import os
import time
import subprocess
from datetime import datetime, timedelta
from google import genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database path
IMESSAGE_DB = os.path.expanduser("~/Library/Messages/chat.db")

# Track the last processed message ID
LAST_MESSAGE_ID_FILE = "last_message_id.txt"

# API Key rotation
class APIKeyRotator:
    def __init__(self):
        self.keys = []
        self.current_index = 0
        
        # Load all GEMINI_API_KEY_* from environment
        i = 1
        while True:
            key = os.getenv(f'GEMINI_API_KEY_{i}')
            if key:
                self.keys.append(key)
                i += 1
            else:
                break
        
        # Fallback to single GEMINI_API_KEY if no numbered keys
        if not self.keys:
            single_key = os.getenv('GEMINI_API_KEY')
            if single_key:
                self.keys.append(single_key)
        
        if not self.keys:
            raise ValueError("No API keys found in .env file")
        
        print(f"🔑 Loaded {len(self.keys)} API key(s)")
    
    def get_current_key(self):
        return self.keys[self.current_index]
    
    def rotate(self):
        """Switch to the next API key"""
        old_index = self.current_index
        self.current_index = (self.current_index + 1) % len(self.keys)
        print(f"🔄 Rotating API key: {old_index + 1} → {self.current_index + 1}")
        return self.get_current_key()

def get_last_processed_message_id():
    """Get the last message ID we processed"""
    if os.path.exists(LAST_MESSAGE_ID_FILE):
        with open(LAST_MESSAGE_ID_FILE, 'r') as f:
            return int(f.read().strip())
    return 0

def save_last_processed_message_id(message_id):
    """Save the last processed message ID"""
    with open(LAST_MESSAGE_ID_FILE, 'w') as f:
        f.write(str(message_id))

def check_for_grok_mentions(last_id):
    """Check for new messages containing @grok"""
    conn = sqlite3.connect(f"file:{IMESSAGE_DB}?mode=ro", uri=True)
    cursor = conn.cursor()
    
    # Look for messages after last_id that contain @grok
    # Search in both text field and attributedBody (hex pattern 4067726F6B = @grok)
    query = """
    SELECT 
        m.ROWID,
        m.text,
        m.attributedBody,
        m.is_from_me,
        cmj.chat_id,
        c.chat_identifier,
        c.display_name,
        c.guid
    FROM message m
    LEFT JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
    LEFT JOIN chat c ON cmj.chat_id = c.ROWID
    WHERE m.ROWID > ?
        AND (
            m.text LIKE '%@grok%' 
            OR m.text LIKE '%grok%'
            OR hex(m.attributedBody) LIKE '%4067726F6B%'
            OR hex(m.attributedBody) LIKE '%67726F6B%'
        )
    ORDER BY m.ROWID ASC
    """
    
    cursor.execute(query, (last_id,))
    mentions = cursor.fetchall()
    conn.close()
    
    return mentions

def get_chat_messages(chat_id, limit=60):
    """Get recent messages from a chat for summarization"""
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
        # Extract text
        message_text = text
        if not message_text and attributed_body:
            try:
                decoded = attributed_body.decode('utf-8', errors='ignore')
                if 'NSString' in decoded:
                    parts = decoded.split('NSString')
                    for part in parts[1:]:
                        cleaned = ''.join(c for c in part if c.isprintable())
                        if len(cleaned) > 2:
                            message_text = cleaned[:200]
                            break
            except:
                pass
        
        if not message_text:
            continue
        
        # Skip messages that contain @grok or grok command
        message_lower = message_text.lower()
        if '@grok' in message_lower or (message_lower.strip().startswith('grok') and len(message_lower.strip().split()) <= 2):
            continue
            
        readable_date = datetime(2001, 1, 1) + timedelta(seconds=date/1e9)
        sender = "Me" if is_from_me else (sender_id or "Other")
        
        formatted_messages.append({
            'text': message_text,
            'sender': sender,
            'date': readable_date,
            'is_from_me': is_from_me
        })
    
    return formatted_messages

def generate_summary(messages, api_key, is_group_chat=True):
    """Generate summary using Gemini"""
    os.environ['GOOGLE_API_KEY'] = api_key
    client = genai.Client()
    
    conversation = []
    for msg in messages:
        timestamp = msg['date'].strftime("%Y-%m-%d %H:%M")
        conversation.append(f"[{timestamp}] {msg['sender']}: {msg['text']}")
    
    conversation_text = "\n".join(conversation)
    
    # Context-aware prompt based on chat type
    chat_type = "group chat" if is_group_chat else "conversation"
    prompt = f"""Summarize this {chat_type} in 3-4 sentences. Don't specify "me". You can reference specific moments, don't be too vague:

{conversation_text}

Summary:"""
    
    # Debug logging
    print(f"\n   📊 DEBUG - Gemini Request Details:")
    print(f"      Messages: {len(messages)}")
    print(f"      Conversation length: {len(conversation_text)} chars")
    print(f"      Total prompt length: {len(prompt)} chars")
    print(f"\n   📝 DEBUG - Conversation being sent:")
    print(f"   {'-'*60}")
    for line in conversation_text.split('\n')[:10]:  # Show first 10 messages
        print(f"   {line}")
    if len(conversation) > 10:
        print(f"   ... and {len(conversation) - 10} more messages")
    print(f"   {'-'*60}\n")
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text

def is_rate_limit_error(error):
    """Check if error is a rate limit error"""
    error_str = str(error).lower()
    return any(phrase in error_str for phrase in [
        'rate limit',
        'quota',
        'too many requests',
        '429',
        'resource_exhausted'
    ])

def send_imessage(chat_identifier, message, is_group_chat=False):
    """Send an iMessage using AppleScript"""
    # Check if it's a group chat (guid format) or individual (phone/email)
    if is_group_chat:
        # Group chat - use guid with chat id
        print(f"   Using group chat mode with identifier: {chat_identifier}")
        applescript = f'''
        on run argv
            set theMessage to item 1 of argv
            tell application "Messages"
                send theMessage to chat id "{chat_identifier}"
            end tell
        end run
        '''
    else:
        # Individual chat - use buddy with phone/email
        print(f"   Using individual chat mode with identifier: {chat_identifier}")
        applescript = f'''
        on run argv
            set theMessage to item 1 of argv
            tell application "Messages"
                set targetService to 1st service whose service type = iMessage
                set targetBuddy to buddy "{chat_identifier}" of targetService
                send theMessage to targetBuddy
            end tell
        end run
        '''
    
    try:
        result = subprocess.run(['osascript', '-e', applescript, message], check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to send message: {e}")
        if hasattr(e, 'stderr') and e.stderr:
            print(f"   stderr: {e.stderr}")
        return False

def monitor_loop():
    """Main monitoring loop"""
    print("🤖 Grok Monitor Starting...")
    print("   Watching for @grok mentions in iMessage\n")
    
    # Initialize API key rotator
    try:
        key_rotator = APIKeyRotator()
    except ValueError as e:
        print(f"❌ {e}")
        return
    
    last_id = get_last_processed_message_id()
    print(f"📍 Starting from message ID: {last_id}")
    print("   Press Ctrl+C to stop\n")
    
    try:
        while True:
            mentions = check_for_grok_mentions(last_id)
            
            for mention in mentions:
                msg_id, text, attr_body, is_from_me, chat_id, chat_identifier, display_name, guid = mention
                
                chat_name = display_name or chat_identifier or "Unknown"
                is_group_chat = chat_identifier.startswith('chat')
                print(f"\n🔔 @grok mentioned in: {chat_name}")
                print(f"   Chat ID: {chat_id}, Message ID: {msg_id}")
                print(f"   DEBUG - chat_identifier: {chat_identifier}")
                print(f"   DEBUG - guid: {guid}")
                print(f"   DEBUG - is_group_chat: {is_group_chat}")
                
                # Get recent messages for summary
                print(f"   Fetching recent messages...")
                messages = get_chat_messages(chat_id, limit=60)
                
                if not messages:
                    print(f"   ⚠️  No messages to summarize")
                    last_id = msg_id
                    save_last_processed_message_id(last_id)
                    continue
                
                print(f"   Found {len(messages)} messages to summarize")
                
                # Generate summary with retry logic for rate limiting
                print(f"   🤔 Generating summary with Gemini...")
                summary = None
                max_retries = len(key_rotator.keys)
                
                for retry in range(max_retries):
                    try:
                        current_key = key_rotator.get_current_key()
                        summary = generate_summary(messages, current_key, is_group_chat)
                        print(f"   ✅ Summary generated!")
                        print(f"\n   Summary Preview:")
                        print(f"   {summary[:200]}...\n")
                        break
                    except Exception as e:
                        if is_rate_limit_error(e):
                            print(f"   ⚠️  Rate limit hit on key {key_rotator.current_index + 1}")
                            if retry < max_retries - 1:
                                key_rotator.rotate()
                                print(f"   🔄 Retrying with next key...")
                                time.sleep(1)
                                continue
                            else:
                                print(f"   ❌ All API keys rate limited!")
                                raise
                        else:
                            print(f"   ❌ Error: {e}")
                            raise
                
                if summary:
                    try:
                    
                        # Send response - use guid for group chats, chat_identifier for individual
                        send_to = guid if is_group_chat else chat_identifier
                        print(f"   DEBUG - send_to: {send_to}")
                        print(f"   📤 Attempting to send response...")
                        success = send_imessage(send_to, f"📝 Chat Summary:\n\n{summary}", is_group_chat)
                        
                        if success:
                            print(f"   ✅ Response sent!")
                        else:
                            print(f"   ℹ️  For group chats, you may need to send manually")
                            print(f"\n   Copy this to send:")
                            print(f"   {'-'*60}")
                            print(f"   {summary}")
                            print(f"   {'-'*60}\n")
                    except Exception as e:
                        print(f"   ❌ Error sending message: {e}")
                
                # Update last processed ID
                last_id = msg_id
                save_last_processed_message_id(last_id)
            
            # Sleep before next check
            time.sleep(2)  # Check every 2 seconds
            
    except KeyboardInterrupt:
        print("\n\n👋 Grok Monitor stopped")
        save_last_processed_message_id(last_id)

if __name__ == "__main__":
    monitor_loop()
