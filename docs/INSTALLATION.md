# Installation Guide

This guide provides detailed instructions for installing and setting up the FitGirl Updater application.

## Prerequisites

### System Requirements

- **Operating System**: Windows 10/11, macOS 10.15+, or Linux (Ubuntu 18.04+)
- **Python**: Version 3.10 or higher
- **Memory**: Minimum 2GB RAM (4GB recommended)
- **Storage**: At least 1GB free space
- **Browser**: Chrome or Chromium (for Selenium automation)

### Software Dependencies

- **Python 3.10+**: Download from [python.org](https://www.python.org/downloads/)
- **Git**: For cloning the repository
- **Docker** (optional): For containerized deployment

## Installation Methods

### Method 1: Local Development Setup

#### Step 1: Clone the Repository

```bash
git clone https://github.com/ravioldev/fitgirl-downloader.git
cd firgirl-updater
```

#### Step 2: Create Virtual Environment

**Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

#### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

#### Step 4: Configure the Application

1. **Edit configuration file:**
   ```bash
   # Windows
   notepad config.yaml
   
   # macOS/Linux
   nano config.yaml
   ```

2. **Basic configuration:**
   ```yaml
   # Web server settings
   web_host: "127.0.0.1"  # Use "0.0.0.0" for external access
   web_port: 2121
   debug_mode: false
   
   # Scraping settings
   max_concurrent_requests: 5
   timeout: 30
   
   # Database settings
   database_file: "fitgirl_releases.json"
   ```

#### Step 5: Run the Application

```bash
python app.py
```

#### Step 6: Access the Web Interface

Open your browser and navigate to: `http://localhost:2121`

### Method 2: Docker Deployment

#### Prerequisites

1. **Install Docker Desktop:**
   - Windows/macOS: Download from [docker.com](https://www.docker.com/products/docker-desktop)
   - Linux: Follow [Docker installation guide](https://docs.docker.com/engine/install/)

2. **Verify Docker installation:**
   ```bash
   docker --version
   docker-compose --version
   ```

#### Step 1: Clone and Navigate

```bash
git clone https://github.com/ravioldev/fitgirl-downloader.git
cd firgirl-updater
```

#### Step 2: Build and Run

```bash
# Build the Docker image
docker-compose build

# Start the application
docker-compose up -d

# Check logs
docker-compose logs -f fitgirl-updater
```

#### Step 3: Access the Application

Open your browser and navigate to: `http://localhost:2121`

#### Step 4: Management Commands

```bash
# Stop the application
docker-compose down

# Restart the application
docker-compose restart

# Update and rebuild
docker-compose up -d --build

# View logs
docker-compose logs -f
```

## Configuration Options

### Web Server Configuration

```yaml
web_host: "0.0.0.0"  # Bind to all interfaces
web_port: 2121        # Port number
debug_mode: false      # Enable debug mode
```

### Scraping Configuration

```yaml
max_concurrent_requests: 5  # Number of concurrent requests
timeout: 30                 # Request timeout (seconds)
```



## Troubleshooting

### Common Issues

#### 1. Python Version Issues

**Problem**: `python: command not found` or version too old

**Solution**:
```bash
# Check Python version
python --version

# Install Python 3.10+ if needed
# Windows: Download from python.org
# macOS: brew install python@3.10
# Ubuntu: sudo apt install python3.10
```

#### 2. Virtual Environment Issues

**Problem**: `venv: command not found`

**Solution**:
```bash
# Install venv module
python -m pip install --upgrade pip
python -m pip install virtualenv
```

#### 3. Chrome/Selenium Issues

**Problem**: Selenium can't find Chrome

**Solution**:
1. **Install Chrome/Chromium**
2. **Verify Chrome installation:**
   ```bash
   # Windows
   "C:\Program Files\Google\Chrome\Application\chrome.exe" --version
   
   # macOS
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version
   
   # Linux
   google-chrome --version
   ```

#### 4. Port Already in Use

**Problem**: `Address already in use`

**Solution**:
```bash
# Change port in config.yaml
web_port: 2122

# Or kill the process using the port
# Windows
netstat -ano | findstr :2121
taskkill /PID <PID> /F

# macOS/Linux
lsof -i :2121
kill -9 <PID>
```

#### 5. Docker Issues

**Problem**: Docker container fails to start

**Solution**:
```bash
# Check Docker logs
docker-compose logs fitgirl-updater

# Rebuild container
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Check system resources
docker system df
docker system prune
```

### Performance Optimization

#### For Large Databases

1. **Increase memory limits:**
   ```yaml
   # In docker-compose.yml
   deploy:
     resources:
       limits:
         memory: 2G
   ```

2. **Optimize scraping settings:**
   ```yaml
   max_concurrent_requests: 3
   ```

#### For Development

1. **Enable debug mode:**
   ```yaml
   debug_mode: true
   ```

2. **Use development database:**
   ```yaml
   database_file: "fitgirl_releases_dev.json"
   ```

## Security Considerations

### Production Deployment

1. **Use HTTPS:**
   - Set up reverse proxy with SSL
   - Use environment variables for secrets

2. **Network Security:**
   - Bind to localhost only: `web_host: "127.0.0.1"`
   - Use firewall rules
   - Consider VPN access

3. **File Permissions:**
   ```bash
   # Set proper permissions
   chmod 600 config.yaml
   chmod 644 fitgirl_releases.json
   ```

### Data Backup

1. **Regular backups:**
   ```bash
   # Backup database
   cp fitgirl_releases.json fitgirl_releases_backup_$(date +%Y%m%d).json
   
   # Backup configuration
   cp config.yaml config_backup_$(date +%Y%m%d).yaml
   ```

2. **Automated backups:**
   ```bash
   # Create backup script
   #!/bin/bash
   DATE=$(date +%Y%m%d_%H%M%S)
   cp fitgirl_releases.json "backups/fitgirl_releases_$DATE.json"
   ```

## Next Steps

After successful installation:

1. **First Run**: Perform initial synchronization
2. **Configuration**: Adjust settings as needed
3. **Monitoring**: Check logs for any issues
4. **Updates**: Keep the application updated

For additional help, see the [Troubleshooting Guide](TROUBLESHOOTING.md) or [API Documentation](API.md). 