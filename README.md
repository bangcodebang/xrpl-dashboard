XRPL Real-Time Analytics Dashboard
A free, open-source dashboard built with Streamlit to monitor the XRP Ledger (XRPL) in real time. View live XRP transactions, detect whale activity, visualize network stats, and look up account information—all with a modern UI and absolutely no API keys required.

🚀 Features
🔄 Real-time XRP Ledger transaction streaming (WebSocket API)

🐋 Whale transaction detection (configurable threshold)

📈 Live metrics: transactions per minute, volume, active accounts

🔍 Easy account lookup (see balance, sequence, etc.)

📊 Interactive charts for transaction volume

⚡ Auto-refresh & metric controls

💸 100% free to run locally

🖥️ Tech Stack
Python 3.9+

Streamlit

websockets

Plotly

pandas

requests

🛠️ Installation
Clone this repo:

bash
git clone https://github.com/yourusername/xrpl-dashboard.git
cd xrpl-dashboard
Install dependencies:

bash
pip install -r requirements.txt
Run the dashboard:

bash
streamlit run xrpl_dashboard.py
🕹️ Usage
Click "Connect to XRPL" in the sidebar to start monitoring live transactions.

Use the whale threshold and refresh sliders to control behavior.

Look up any XRP address instantly.

Filter for only whale transactions if desired.

📦 Files
File	Purpose
xrpl_dashboard.py	Main Streamlit dashboard app
requirements.txt	Python dependencies
README.md	This documentation
setup.sh	(optional) Quick setup script for Unix/Mac
💡 Notes
No API keys or paid services required—uses public XRPL endpoints.

To run on Windows, just use pip/Streamlit as above (no setup.sh needed).

You can deploy on Streamlit Cloud or Heroku if you want free hosting!

📝 License
This project is open-source and free to use, share, or modify.

Feel free to personalize further with your name, repo link, or screenshots!
