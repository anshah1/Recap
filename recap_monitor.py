#!/usr/bin/env python3
"""
Recap Monitor - Watches for @recap mentions in iMessage and auto-responds with summaries
"""

import sqlite3
import os
import time
import subprocess
import re
from datetime import datetime, timedelta
from google import genai
from dotenv import load_dotenv

load_dotenv()

IMESSAGE_DB = os.path.expanduser("~/Library/Messages/chat.db")
class APIKeyRotator:
    def __init__(self):
        self.keys = []
        self.current_index = 0
        
        i = 1
        while True:
            key = os.getenv(f'GEMINI_API_KEY_{i}')
            if key:
                self.keys.append(key)
                i += 1
            else:
                break
        
        if not self.keys:
            single_key = os.getenv('GEMINI_API_KEY')
            if single_key:
                self.keys.append(single_key)
        
        if not self.keys:
            raise ValueError("No API keys found in .env file")
        
        print(f"Loaded {len(self.keys)} API key(s)")
    
    def get_current_key(self):
        return self.keys[self.current_index]
    
    def rotate(self):
        old_index = self.current_index
        self.current_index = (self.current_index + 1) % len(self.keys)
        print(f"Switching to API key {self.current_index + 1}/{len(self.keys)}")
        return self.get_current_key()

def get_current_max_message_id():
    """Get the latest message ID from the database"""
    try:
        conn = sqlite3.connect(f"file:{IMESSAGE_DB}?mode=ro", uri=True)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(ROWID) FROM message")
        result = cursor.fetchone()
        conn.close()
        return result[0] if result[0] else 0
    except Exception as e:
        print(f"Warning: Could not get max message ID: {e}")
        return 0

def has_new_messages(last_id):
    try:
        conn = sqlite3.connect(f"file:{IMESSAGE_DB}?mode=ro", uri=True)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(ROWID) FROM message")
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            return result[0] > last_id
        return False
    except Exception as e:
        print(f"Error checking for new messages: {e}")
        return False

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
    except:
        pass
    return None

def check_for_recap_mentions(last_id):
    conn = sqlite3.connect(f"file:{IMESSAGE_DB}?mode=ro", uri=True)
    cursor = conn.cursor()
    
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
            m.text LIKE '%@recap%' 
            OR m.text LIKE '%recap%'
            OR hex(m.attributedBody) LIKE '%407265636170%'
            OR hex(m.attributedBody) LIKE '%7265636170%'
        )
    ORDER BY m.ROWID ASC
    """
    
    cursor.execute(query, (last_id,))
    mentions = cursor.fetchall()
    conn.close()
    
    return mentions

def parse_recap_limit(text, attributed_body):
    message_text = text or extract_text_from_attributed_body(attributed_body)
    
    if not message_text:
        return 60
    
    match = re.search(r'@?recap\s*(\d+)', message_text.lower())
    if match:
        limit = int(match.group(1))
        return min(max(limit, 10), 500)
    
    return 60 

def get_chat_messages(chat_id, limit=60):
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
    
    messages.reverse()
    
    formatted_messages = []
    for text, attributed_body, is_from_me, date, sender_id in messages:
        message_text = text or extract_text_from_attributed_body(attributed_body)
        
        if not message_text:
            continue
        
        message_lower = message_text.lower()
        if '@recap' in message_lower or (message_lower.strip().startswith('recap') and len(message_lower.strip().split()) <= 2):
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
    os.environ['GOOGLE_API_KEY'] = api_key
    client = genai.Client()
    
    conversation = []
    for msg in messages:
        timestamp = msg['date'].strftime("%Y-%m-%d %H:%M")
        conversation.append(f"[{timestamp}] {msg['sender']}: {msg['text']}")
    
    conversation_text = "\n".join(conversation)
    
    chat_type = "group chat" if is_group_chat else "conversation"
    prompt = f"""Summarize this {chat_type} in 3-4 sentences. Don't specify "me". You can reference specific moments, don't be too vague:

{conversation_text}

Summary:"""
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text

def is_rate_limit_error(error):
    error_str = str(error)
    return '429' in error_str or 'Too Many Requests' in error_str

def send_imessage(chat_identifier, message, is_group_chat=False):
    if is_group_chat:
        applescript = f'''
        on run argv
            set theMessage to item 1 of argv
            tell application "Messages"
                send theMessage to chat id "{chat_identifier}"
            end tell
        end run
        '''
    else:
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
        print(f"Error sending recap: {e}")
        return False

def monitor_loop():
    print("Recap Monitor Starting...")
    print("Watching for @recap mentions in iMessage\n")
    
    try:
        key_rotator = APIKeyRotator()
    except ValueError as e:
        print(f"Error: {e}")
        return
    
    last_id = get_current_max_message_id()
    print(f"Monitoring started (message ID: {last_id})")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            if not has_new_messages(last_id):
                time.sleep(2)
                continue
            
            mentions = check_for_recap_mentions(last_id)
            
            for mention in mentions:
                msg_id, text, attr_body, is_from_me, chat_id, chat_identifier, display_name, guid = mention
                
                chat_name = display_name or chat_identifier or "Unknown"
                is_group_chat = chat_identifier.startswith('chat')
                message_limit = parse_recap_limit(text, attr_body)
                
                print(f"\nRecap requested in '{chat_name}' for {message_limit} messages")
                
                messages = get_chat_messages(chat_id, limit=message_limit)
                
                if not messages:
                    print(f"No messages to recap")
                    last_id = msg_id
                    continue
                
                summary = None
                max_retries = len(key_rotator.keys)
                
                for retry in range(max_retries):
                    try:
                        current_key = key_rotator.get_current_key()
                        summary = generate_summary(messages, current_key, is_group_chat)
                        print("Recap generated")
                        break
                    except Exception as e:
                        if is_rate_limit_error(e):
                            print("Rate limit hit")
                            if retry < max_retries - 1:
                                key_rotator.rotate()
                                time.sleep(1)
                                continue
                            else:
                                print("All API keys rate limited")
                                raise
                        else:
                            print(f"Error generating recap: {e}")
                            raise
                
                if summary:
                    try:
                        send_to = guid if is_group_chat else chat_identifier
                        success = send_imessage(send_to, f"📝 Chat Recap:\n\n{summary}", is_group_chat)
                        
                        if success:
                            print("Recap sent")
                        else:
                            print("Failed to send recap")
                    except Exception as e:
                        print(f"Error sending recap: {e}")
                
                last_id = msg_id
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\nRecap Monitor stopped")

if __name__ == "__main__":
    monitor_loop()