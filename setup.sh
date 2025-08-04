#!/bin/bash
# XRPL Dashboard Setup Script

echo "Setting up XRPL Real-Time Analytics Dashboard..."

# Create virtual environment
python -m venv xrpl_dashboard_env

# Activate virtual environment
source xrpl_dashboard_env/bin/activate  # Linux/Mac
# xrpl_dashboard_env\Scripts\activate  # Windows

# Install requirements
pip install -r requirements.txt

echo "Setup complete!"
echo "To run the dashboard:"
echo "1. Activate the virtual environment: source xrpl_dashboard_env/bin/activate"
echo "2. Run: streamlit run xrpl_dashboard.py"
echo "3. Open your browser to the URL shown in the terminal"
