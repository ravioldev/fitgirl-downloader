#!/bin/bash

# FitGirl Updater Docker Management Script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to build the Docker image
build() {
    print_status "Building FitGirl Updater Docker image..."
    docker-compose build
    if [ $? -eq 0 ]; then
        print_success "Docker image built successfully!"
    else
        print_error "Failed to build Docker image"
        exit 1
    fi
}

# Function to start the container
start() {
    print_status "Starting FitGirl Updater container..."
    docker-compose up -d
    if [ $? -eq 0 ]; then
        print_success "Container started successfully!"
        print_status "Application available at: http://localhost:2121"
    else
        print_error "Failed to start container"
        exit 1
    fi
}

# Function to stop the container
stop() {
    print_status "Stopping FitGirl Updater container..."
    docker-compose down
    if [ $? -eq 0 ]; then
        print_success "Container stopped successfully!"
    else
        print_error "Failed to stop container"
        exit 1
    fi
}

# Function to restart the container
restart() {
    print_status "Restarting FitGirl Updater container..."
    stop
    start
}

# Function to view logs
logs() {
    print_status "Showing container logs (Press Ctrl+C to exit)..."
    docker-compose logs -f fitgirl-updater
}

# Function to check status
status() {
    print_status "Container status:"
    docker-compose ps
    echo ""
    print_status "Resource usage:"
    docker stats fitgirl-updater-app --no-stream
}

# Function to open shell in container
shell() {
    print_status "Opening shell in container..."
    docker-compose exec fitgirl-updater /bin/bash
}

# Function to clean up
cleanup() {
    print_status "Cleaning up Docker resources..."
    docker-compose down -v
    docker image prune -f
    print_success "Cleanup completed!"
}

# Function to rebuild and restart
rebuild() {
    print_status "Rebuilding and restarting application..."
    stop
    build
    start
}

# Help function
show_help() {
    echo "FitGirl Updater Docker Management Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  build     Build the Docker image"
    echo "  start     Start the container"
    echo "  stop      Stop the container"
    echo "  restart   Restart the container"
    echo "  logs      View container logs"
    echo "  status    Show container status and resource usage"
    echo "  shell     Open shell in container"
    echo "  cleanup   Stop container and clean up resources"
    echo "  rebuild   Rebuild image and restart container"
    echo "  help      Show this help message"
}

# Main script logic
case "$1" in
    build)
        build
        ;;
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    logs)
        logs
        ;;
    status)
        status
        ;;
    shell)
        shell
        ;;
    cleanup)
        cleanup
        ;;
    rebuild)
        rebuild
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Invalid command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac 