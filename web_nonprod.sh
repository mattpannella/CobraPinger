#!/bin/bash

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}CobraPinger Web Server Launcher${NC}\n"

#defaults
PORT=8000
WORKERS=3
VENV_PATH="venv"

#parse arguments
while getopts "w:" opt; do
  case $opt in
    w) WORKERS=$OPTARG ;;
    \?) echo "Invalid option: -$OPTARG" >&2; exit 1 ;;
  esac
done

echo -e "${YELLOW}Using $WORKERS workers${NC}"

#create Python virtual environment if it doesn't exist
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv $VENV_PATH
fi

#activate virtual environment
source $VENV_PATH/bin/activate

#install all dependencies from requirements.txt
echo -e "${YELLOW}Installing dependencies from requirements.txt...${NC}"
pip install -r requirements.txt

echo -e "${GREEN}Starting web server on port $PORT...${NC}"
echo -e "Access the site at: http://localhost:$PORT"
echo -e "Press Ctrl+C to stop the server\n"

#start gunicorn tmdwu
gunicorn --workers $WORKERS --bind 0.0.0.0:$PORT wsgi:app