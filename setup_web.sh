#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}CobraPinger Web Setup Script${NC}\n"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (sudo ./setup_web.sh)"
    exit 1
fi

# Prompt for configuration values
read -p "Enter domain name (e.g., cobrapinger.com): " DOMAIN_NAME
read -p "Enter system username that will run the app: " APP_USER
read -p "Enter the path to your existing CobraPinger installation: " INSTALL_PATH

# Verify the installation path exists and has required files
if [ ! -f "$INSTALL_PATH/web.py" ] || [ ! -f "$INSTALL_PATH/wsgi.py" ]; then
    echo "Error: Could not find required files in $INSTALL_PATH"
    exit 1
fi

# Install system dependencies
echo -e "${GREEN}Installing system dependencies...${NC}"
apt-get update
apt-get install -y python3-pip python3-venv nginx

# Create logs directory
echo -e "${GREEN}Setting up log directory...${NC}"
mkdir -p "$INSTALL_PATH/logs"
chown -R $APP_USER:www-data "$INSTALL_PATH/logs"

# Set up Python virtual environment if it doesn't exist
if [ ! -d "$INSTALL_PATH/venv" ]; then
    echo -e "${GREEN}Setting up Python virtual environment...${NC}"
    su - $APP_USER -c "python3 -m venv $INSTALL_PATH/venv"
fi

# Install Python dependencies
echo -e "${GREEN}Installing Python dependencies...${NC}"
su - $APP_USER -c "$INSTALL_PATH/venv/bin/pip install gunicorn flask feedgen flask-wtf markupsafe"

# Create systemd service
echo -e "${GREEN}Creating systemd service...${NC}"
cat > /etc/systemd/system/cobrapinger-web.service << EOF
[Unit]
Description=CobraPinger Web Interface
After=network.target

[Service]
User=$APP_USER
Group=www-data
WorkingDirectory=$INSTALL_PATH
Environment="PATH=$INSTALL_PATH/venv/bin"
ExecStart=$INSTALL_PATH/venv/bin/gunicorn --workers 3 --bind unix:cobrapinger-web.sock -m 007 wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Configure Nginx
echo -e "${GREEN}Configuring Nginx...${NC}"
cat > /etc/nginx/sites-available/cobrapinger << EOF
server {
    listen 80;
    server_name $DOMAIN_NAME;

    location / {
        include proxy_params;
        proxy_pass http://unix:$INSTALL_PATH/cobrapinger-web.sock;
    }

    location /static {
        alias $INSTALL_PATH/static;
    }
}
EOF

# Enable the site
ln -sf /etc/nginx/sites-available/cobrapinger /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Start and enable services
echo -e "${GREEN}Starting services...${NC}"
systemctl daemon-reload
systemctl start cobrapinger-web
systemctl enable cobrapinger-web
systemctl restart nginx

# Install SSL certificate if domain is provided
if [ ! -z "$DOMAIN_NAME" ]; then
    echo -e "${GREEN}Installing SSL certificate...${NC}"
    apt-get install -y certbot python3-certbot-nginx
    certbot --nginx -d $DOMAIN_NAME --non-interactive --agree-tos --redirect
fi

echo -e "\n${GREEN}Setup complete!${NC}"
echo -e "You can now access your site at: https://$DOMAIN_NAME"
echo -e "Check the logs at: $INSTALL_PATH/logs/"
echo -e "To restart the web interface: sudo systemctl restart cobrapinger-web"