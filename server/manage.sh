#!/bin/bash
# OnyxPoker Server Management Script

case "$1" in
    start)
        echo "Starting OnyxPoker server..."
        sudo systemctl start onyxpoker
        sleep 2
        sudo systemctl status onyxpoker --no-pager
        ;;
    stop)
        echo "Stopping OnyxPoker server..."
        sudo systemctl stop onyxpoker
        ;;
    restart)
        echo "Restarting OnyxPoker server..."
        sudo systemctl restart onyxpoker
        sleep 2
        sudo systemctl status onyxpoker --no-pager
        ;;
    status)
        sudo systemctl status onyxpoker --no-pager
        ;;
    logs)
        echo "=== Server Logs (last 50 lines) ==="
        sudo tail -50 /var/log/onyxpoker/server.log
        ;;
    errors)
        echo "=== Error Logs (last 50 lines) ==="
        sudo tail -50 /var/log/onyxpoker/error.log
        ;;
    follow)
        echo "=== Following logs (Ctrl+C to stop) ==="
        sudo tail -f /var/log/onyxpoker/server.log
        ;;
    health)
        curl http://localhost:5000/health
        echo ""
        ;;
    *)
        echo "OnyxPoker Server Management"
        echo "Usage: $0 {start|stop|restart|status|logs|errors|follow|health}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the server"
        echo "  stop    - Stop the server"
        echo "  restart - Restart the server"
        echo "  status  - Show server status"
        echo "  logs    - Show last 50 lines of server logs"
        echo "  errors  - Show last 50 lines of error logs"
        echo "  follow  - Follow logs in real-time"
        echo "  health  - Check server health"
        exit 1
        ;;
esac
