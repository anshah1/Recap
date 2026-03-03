#!/bin/bash

PLIST_FILE="com.recap.monitor.plist"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_FILE"
SOURCE_PLIST="$(cd "$(dirname "$0")" && pwd)/$PLIST_FILE"

case "$1" in
    install)
        echo "📦 Installing Recap Monitor service..."
        mkdir -p "$HOME/Library/LaunchAgents"
        cp "$SOURCE_PLIST" "$PLIST_PATH"
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
