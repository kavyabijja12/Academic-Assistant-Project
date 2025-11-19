#!/bin/bash
# Setup and run script for Academic Assistant

echo "Setting up Academic Assistant..."

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Initialize database if not exists
if [ ! -f "database/appointments.db" ]; then
    echo "Initializing database..."
    python database/init_db.py
fi

# Run Streamlit app
echo "Starting Streamlit app..."
streamlit run main.py


