#!/bin/bash

# Medical Chatbot Startup Script with Logging
# Starts both the FastAPI backend server and Streamlit frontend

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Log files
BACKEND_LOG="backend.log"
FRONTEND_LOG="frontend.log"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Starting Medical Chatbot Application${NC}"
echo -e "${BLUE}========================================${NC}"

# Change to script directory
cd "$(dirname "$0")"

# Clean old logs
rm -f $BACKEND_LOG $FRONTEND_LOG

# Check if .env file exists
if [ ! -f "../.env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    exit 1
fi

# Function to cleanup background processes on exit
cleanup() {
    echo -e "\n${RED}Shutting down services...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# 1. Start FastAPI backend server
echo -e "${GREEN}Starting FastAPI backend... (Logs: $BACKEND_LOG)${NC}"
# Redirect both stdout and stderr (2>&1) to the log file
python main.py > $BACKEND_LOG 2>&1 &
BACKEND_PID=$!

# Wait a bit for backend to start
sleep 3

# Check if backend is running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}Error: Backend server failed to start! Last logs:${NC}"
    tail -n 20 $BACKEND_LOG
    exit 1
fi

# 2. Start Streamlit frontend
echo -e "${GREEN}Starting Streamlit frontend... (Logs: $FRONTEND_LOG)${NC}"
streamlit run app.py > $FRONTEND_LOG 2>&1 &
FRONTEND_PID=$!

sleep 2

# Check if frontend is running
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${RED}Error: Streamlit failed to start! Last logs:${NC}"
    tail -n 20 $FRONTEND_LOG
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}✓ Both services are running!${NC}"
echo -e "${YELLOW}FOLLOWING BACKEND LOGS (Ctrl+C to stop everything):${NC}"
echo -e "${BLUE}========================================${NC}"

# This command lets you see the logs in real-time in your terminal
tail -f $BACKEND_LOG &
TAIL_PID=$!

# Ensure tail stops when script exits
trap "kill $TAIL_PID $BACKEND_PID $FRONTEND_PID; exit" SIGINT SIGTERM

wait