#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (sudo ./web_prod.sh)"
    exit 1
fi

# Get configuration
read -p "Enter domain name (e.g., cobrapinger.com): " DOMAIN_NAME
read -p "Enter system username that will run the app: " APP_USER
read -p "Enter the path to your CobraPinger installation: " INSTALL_PATH

# Install dependencies
echo -e "${YELLOW}Installing system dependencies...${NC}"
apt-get update
apt-get install -y python3-pip python3-venv nginx certbot python3-certbot-nginx

# Set up Python environment
if [ ! -d "$INSTALL_PATH/venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    su - $APP_USER -c "python3 -m venv $INSTALL_PATH/venv"
fi

# Install Python packages
echo -e "${YELLOW}Installing Python dependencies...${NC}"
su - $APP_USER -c "cd $INSTALL_PATH && $INSTALL_PATH/venv/bin/pip install -r requirements.txt"

# Configure Nginx
echo -e "${GREEN}Configuring Nginx...${NC}"
cat > /etc/nginx/sites-available/cobrapinger << EOF
server {
    listen 80;
    server_name $DOMAIN_NAME;

    access_log $INSTALL_PATH/logs/access.log;
    error_log $INSTALL_PATH/logs/error.log;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static {
        alias $INSTALL_PATH/static;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }
}
EOF

# Enable the site
ln -sf /etc/nginx/sites-available/cobrapinger /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Set up SSL
echo -e "${GREEN}Setting up SSL...${NC}"
certbot --nginx -d $DOMAIN_NAME --non-interactive --agree-tos --redirect

# Create start script
cat > "$INSTALL_PATH/start_web.sh" << EOF
#!/bin/bash
source $INSTALL_PATH/venv/bin/activate
echo "Starting CobraPinger Web Server..."
while true; do
    gunicorn --workers 3 --bind 127.0.0.1:8000 wsgi:app
    echo "Server stopped, restarting in 5 seconds..."
    sleep 5
done
EOF

chmod +x "$INSTALL_PATH/start_web.sh"
chown $APP_USER:$APP_USER "$INSTALL_PATH/start_web.sh"

echo -e "\n${GREEN}Setup complete!${NC}"
echo -e "To start the web server: $INSTALL_PATH/start_web.sh"
echo -e "To restart nginx: sudo systemctl restart nginx"
echo -e "Site will be available at: https://$DOMAIN_NAME"