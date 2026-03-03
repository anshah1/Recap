#!/bin/bash

PLIST_FILE="com.recap.monitor.plist"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_FILE"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_PATH="$PROJECT_DIR/.venv/bin/python3"
SCRIPT_PATH="$PROJECT_DIR/recap_monitor.py"
LOG_PATH="$PROJECT_DIR/recap_monitor.log"

case "$1" in
    install)
        echo "📦 Installing Recap Monitor service..."
        mkdir -p "$HOME/Library/LaunchAgents"
        
        # Generate plist with current user's paths
        cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.recap.monitor</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_PATH</string>
        <string>-u</string>
        <string>$SCRIPT_PATH</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>$LOG_PATH</string>
    
    <key>StandardErrorPath</key>
    <string>$LOG_PATH</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
    </dict>
</dict>
</plist>
EOF
        
        launchctl load "$PLIST_PATH"
        echo "✅ Service installed and started"
        echo "   Will auto-start on login/boot"
        ;;
    
    uninstall)
        echo "🗑️  Uninstalling Recap Monitor service..."
        launchctl unload "$PLIST_PATH" 2>/dev/null || true
        rm -f "$PLIST_PATH"
        echo "✅ Service uninstalled"
        ;;
    
    start)
        echo "▶️  Starting Recap Monitor service..."
        launchctl load "$PLIST_PATH"
        echo "✅ Service started"
        ;;
    
    stop)
        echo "⏸️  Stopping Recap Monitor service..."
        launchctl unload "$PLIST_PATH"
        echo "✅ Service stopped"
        ;;
    
    restart)
        echo "🔄 Restarting Recap Monitor service..."
        launchctl unload "$PLIST_PATH" 2>/dev/null || true
        launchctl load "$PLIST_PATH"
        echo "✅ Service restarted"
        ;;
    
    status)
        if launchctl list | grep -q "com.recap.monitor"; then
            echo "✅ Recap Monitor is running"
            echo ""
            echo "📋 Recent logs:"
            tail -n 20 "$(dirname "$0")/recap_monitor.log" 2>/dev/null || echo "No logs yet"
        else
            echo "❌ Recap Monitor is not running"
        fi
        ;;
    
    logs)
        LOG_FILE="$(dirname "$0")/recap_monitor.log"
        if [ -f "$LOG_FILE" ]; then
            echo "📋 Showing logs (Ctrl+C to exit):"
            tail -f "$LOG_FILE"
        else
            echo "❌ No log file found"
        fi
        ;;
    
    *)
        echo "Recap Monitor Service Manager"
        echo ""
        echo "Usage: $0 {install|uninstall|start|stop|restart|status|logs}"
        echo ""
        echo "Commands:"
        echo "  install   - Install and start the service (auto-starts on boot)"
        echo "  uninstall - Stop and remove the service"
        echo "  start     - Start the service"
        echo "  stop      - Stop the service"
        echo "  restart   - Restart the service"
        echo "  status    - Check if service is running"
        echo "  logs      - View live logs"
        exit 1
        ;;
esac
