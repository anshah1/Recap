#!/bin/bash
# Helper script to send iMessage via AppleScript

RECIPIENT="$1"
MESSAGE="$2"

if [ -z "$RECIPIENT" ] || [ -z "$MESSAGE" ]; then
    echo "Usage: ./send_imessage.sh <phone_number_or_email> <message>"
    exit 1
fi

osascript <<EOF
tell application "Messages"
    set targetService to 1st service whose service type = iMessage
    set targetBuddy to buddy "$RECIPIENT" of targetService
    send "$MESSAGE" to targetBuddy
end tell
EOF

echo "Message sent to $RECIPIENT"
