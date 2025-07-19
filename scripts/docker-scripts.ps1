# FitGirl Updater Docker Management Script for Windows PowerShell

param(
    [Parameter(Mandatory=$false)]
    [string]$Command
)

# Function to print colored output
function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Function to build the Docker image
function Build-Image {
    Write-Status "Building FitGirl Updater Docker image..."
    docker-compose build
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker image built successfully!"
    } else {
        Write-Error-Custom "Failed to build Docker image"
        exit 1
    }
}

# Function to start the container
function Start-Container {
    Write-Status "Starting FitGirl Updater container..."
    docker-compose up -d
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Container started successfully!"
        Write-Status "Application available at: http://localhost:2121"
    } else {
        Write-Error-Custom "Failed to start container"
        exit 1
    }
}

# Function to stop the container
function Stop-Container {
    Write-Status "Stopping FitGirl Updater container..."
    docker-compose down
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Container stopped successfully!"
    } else {
        Write-Error-Custom "Failed to stop container"
        exit 1
    }
}

# Function to restart the container
function Restart-Container {
    Write-Status "Restarting FitGirl Updater container..."
    Stop-Container
    Start-Container
}

# Function to view logs
function Show-Logs {
    Write-Status "Showing container logs (Press Ctrl+C to exit)..."
    docker-compose logs -f fitgirl-updater
}

# Function to check status
function Show-Status {
    Write-Status "Container status:"
    docker-compose ps
    Write-Host ""
    Write-Status "Resource usage:"
    docker stats fitgirl-updater-app --no-stream
}

# Function to open shell in container
function Open-Shell {
    Write-Status "Opening shell in container..."
    docker-compose exec fitgirl-updater /bin/bash
}

# Function to clean up
function Cleanup-Resources {
    Write-Status "Cleaning up Docker resources..."
    docker-compose down -v
    docker image prune -f
    Write-Success "Cleanup completed!"
}

# Function to rebuild and restart
function Rebuild-All {
    Write-Status "Rebuilding and restarting application..."
    Stop-Container
    Build-Image
    Start-Container
}

# Help function
function Show-Help {
    Write-Host "FitGirl Updater Docker Management Script for Windows" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\docker-scripts.ps1 [COMMAND]" -ForegroundColor White
    Write-Host ""
    Write-Host "Commands:" -ForegroundColor White
    Write-Host "  build     Build the Docker image" -ForegroundColor Gray
    Write-Host "  start     Start the container" -ForegroundColor Gray
    Write-Host "  stop      Stop the container" -ForegroundColor Gray
    Write-Host "  restart   Restart the container" -ForegroundColor Gray
    Write-Host "  logs      View container logs" -ForegroundColor Gray
    Write-Host "  status    Show container status and resource usage" -ForegroundColor Gray
    Write-Host "  shell     Open shell in container" -ForegroundColor Gray
    Write-Host "  cleanup   Stop container and clean up resources" -ForegroundColor Gray
    Write-Host "  rebuild   Rebuild image and restart container" -ForegroundColor Gray
    Write-Host "  help      Show this help message" -ForegroundColor Gray
}

# Main script logic
switch ($Command.ToLower()) {
    "build" {
        Build-Image
    }
    "start" {
        Start-Container
    }
    "stop" {
        Stop-Container
    }
    "restart" {
        Restart-Container
    }
    "logs" {
        Show-Logs
    }
    "status" {
        Show-Status
    }
    "shell" {
        Open-Shell
    }
    "cleanup" {
        Cleanup-Resources
    }
    "rebuild" {
        Rebuild-All
    }
    "help" {
        Show-Help
    }
    default {
        if ([string]::IsNullOrEmpty($Command)) {
            Show-Help
        } else {
            Write-Error-Custom "Invalid command: $Command"
            Write-Host ""
            Show-Help
            exit 1
        }
    }
} 