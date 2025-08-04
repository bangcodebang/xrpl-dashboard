
import streamlit as st
import asyncio
import websockets
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import time
from collections import defaultdict, deque
import threading
import queue

# Page configuration
st.set_page_config(
    page_title="XRPL Real-Time Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 1rem;
    }
    
    .whale-indicator {
        background-color: #ff6b35;
        color: white;
        padding: 2px 8px;
        border-radius: 15px;
        font-size: 12px;
        font-weight: bold;
    }
    
    .transaction-row {
        border-bottom: 1px solid #eee;
        padding: 10px 0;
    }
    
    .status-connected {
        color: #28a745;
    }
    
    .status-disconnected {
        color: #dc3545;
    }
    
    .stMetric {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
    }
</style>
""", unsafe_allow_html=True)

class XRPLDashboard:
    def __init__(self):
        self.ws_url = "wss://xrplcluster.com"
        self.whale_threshold = 10000
        self.max_transactions = 100
        self.transactions = deque(maxlen=self.max_transactions)
        self.whale_transactions = deque(maxlen=50)
        self.metrics = {
            'total_transactions': 0,
            'whale_count': 0,
            'total_volume': 0,
            'active_accounts': set()
        }
        self.connection_status = "Disconnected"
        self.current_ledger = 0
        self.xrp_price = 0
        self.transaction_queue = queue.Queue()
        self.is_running = False
        
    def get_xrp_price(self):
        """Fetch current XRP price from CoinGecko API"""
        try:
            response = requests.get(
                "https://api.coingecko.com/api/v3/simple/price?ids=ripple&vs_currencies=usd",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                return data['ripple']['usd']
        except Exception as e:
            st.error(f"Error fetching XRP price: {e}")
        return 0
    
    def parse_transaction(self, tx_data):
        """Parse transaction data and extract relevant information"""
        if not tx_data.get('validated', False):
            return None
            
        tx = tx_data.get('transaction', {})
        meta = tx_data.get('meta', {})
        
        # Extract basic info
        tx_type = tx.get('TransactionType', 'Unknown')
        account = tx.get('Account', '')
        destination = tx.get('Destination', '')
        amount = 0
        is_whale = False
        
        # Parse amount for Payment transactions
        if tx_type == 'Payment' and tx.get('Amount'):
            if isinstance(tx['Amount'], str):
                try:
                    amount = int(tx['Amount']) / 1_000_000  # Convert drops to XRP
                    if amount >= self.whale_threshold:
                        is_whale = True
                except (ValueError, TypeError):
                    amount = 0
        
        # Get transaction result
        result = meta.get('TransactionResult', 'Unknown')
        
        return {
            'timestamp': datetime.now(),
            'type': tx_type,
            'account': account,
            'destination': destination,
            'amount': amount,
            'result': result,
            'is_whale': is_whale,
            'ledger_index': tx_data.get('ledger_index', 0)
        }
    
    def update_metrics(self, parsed_tx):
        """Update dashboard metrics with new transaction"""
        if not parsed_tx:
            return
            
        self.metrics['total_transactions'] += 1
        
        if parsed_tx['is_whale']:
            self.metrics['whale_count'] += 1
            
        if parsed_tx['amount'] > 0:
            self.metrics['total_volume'] += parsed_tx['amount']
            
        if parsed_tx['account']:
            self.metrics['active_accounts'].add(parsed_tx['account'])
        if parsed_tx['destination']:
            self.metrics['active_accounts'].add(parsed_tx['destination'])
    
    async def websocket_handler(self):
        """Handle WebSocket connection and message processing"""
        try:
            async with websockets.connect(self.ws_url) as websocket:
                self.connection_status = "Connected"
                
                # Subscribe to streams
                subscribe_msg = {
                    "id": "dashboard_subscription",
                    "command": "subscribe",
                    "streams": ["transactions", "ledger"]
                }
                await websocket.send(json.dumps(subscribe_msg))
                
                # Get server info
                server_info_msg = {
                    "id": "server_info",
                    "command": "server_info"
                }
                await websocket.send(json.dumps(server_info_msg))
                
                async for message in websocket:
                    if not self.is_running:
                        break
                        
                    try:
                        data = json.loads(message)
                        await self.process_message(data)
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            self.connection_status = f"Error: {str(e)}"
            st.error(f"WebSocket error: {e}")
    
    async def process_message(self, data):
        """Process incoming WebSocket messages"""
        msg_type = data.get('type')
        
        if msg_type == 'transaction':
            parsed_tx = self.parse_transaction(data)
            if parsed_tx:
                self.transactions.append(parsed_tx)
                if parsed_tx['is_whale']:
                    self.whale_transactions.append(parsed_tx)
                self.update_metrics(parsed_tx)
                self.transaction_queue.put(parsed_tx)
                
        elif msg_type == 'ledgerClosed':
            self.current_ledger = data.get('ledger_index', 0)
            
        elif data.get('id') == 'server_info' and data.get('result'):
            # Process server info response
            pass
    
    def get_account_info(self, address):
        """Get account information via REST API"""
        try:
            url = f"https://s1.ripple.com:51234/"
            payload = {
                "method": "account_info",
                "params": [{
                    "account": address,
                    "ledger_index": "validated"
                }]
            }
            
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('result', {}).get('status') == 'success':
                    account_data = data['result']['account_data']
                    balance = int(account_data.get('Balance', 0)) / 1_000_000
                    return {
                        'balance': balance,
                        'sequence': account_data.get('Sequence', 0),
                        'flags': account_data.get('Flags', 0)
                    }
        except Exception as e:
            st.error(f"Error fetching account info: {e}")
        return None

# Initialize dashboard
@st.cache_resource
def get_dashboard():
    return XRPLDashboard()

dashboard = get_dashboard()

# Sidebar
st.sidebar.title("🔧 Dashboard Controls")

# Auto-refresh toggle
auto_refresh = st.sidebar.checkbox("Auto Refresh", value=True)
if auto_refresh:
    refresh_rate = st.sidebar.slider("Refresh Rate (seconds)", 1, 10, 3)

# Whale threshold setting
dashboard.whale_threshold = st.sidebar.number_input(
    "Whale Threshold (XRP)", 
    min_value=1000, 
    max_value=100000, 
    value=10000, 
    step=1000
)

# Connection controls
if st.sidebar.button("🔌 Connect to XRPL"):
    dashboard.is_running = True
    dashboard.xrp_price = dashboard.get_xrp_price()
    
    # Start WebSocket in background thread
    def run_websocket():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(dashboard.websocket_handler())
    
    threading.Thread(target=run_websocket, daemon=True).start()
    st.sidebar.success("Connecting to XRPL...")

if st.sidebar.button("🔌 Disconnect"):
    dashboard.is_running = False
    dashboard.connection_status = "Disconnected"
    st.sidebar.info("Disconnected from XRPL")

# Main Dashboard
st.markdown("""
<div class="main-header">
    <h1>📊 XRPL Real-Time Analytics Dashboard</h1>
    <p>Real-time XRP Ledger transaction monitoring and whale detection</p>
</div>
""", unsafe_allow_html=True)

# Status row
col1, col2, col3, col4 = st.columns(4)

with col1:
    status_color = "🟢" if dashboard.connection_status == "Connected" else "🔴"
    st.metric("Connection Status", f"{status_color} {dashboard.connection_status}")

with col2:
    st.metric("Current Ledger", f"{dashboard.current_ledger:,}")

with col3:
    st.metric("XRP Price", f"${dashboard.xrp_price:.4f}")

with col4:
    st.metric("Active Accounts", len(dashboard.metrics['active_accounts']))

# Metrics Row
st.subheader("📈 Live Metrics")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Transactions", 
        dashboard.metrics['total_transactions'],
        delta=None
    )

with col2:
    st.metric(
        "Whale Transactions", 
        dashboard.metrics['whale_count'],
        delta=None
    )

with col3:
    st.metric(
        "Total Volume (XRP)", 
        f"{dashboard.metrics['total_volume']:,.0f}",
        delta=None
    )

with col4:
    transaction_rate = len([tx for tx in dashboard.transactions if tx['timestamp'] > datetime.now() - timedelta(minutes=1)])
    st.metric(
        "Transactions/Min", 
        transaction_rate,
        delta=None
    )

# Main content area
col1, col2 = st.columns([2, 1])

# Transaction Feed
with col1:
    st.subheader("🔄 Live Transaction Feed")
    
    # Filter options
    show_whales_only = st.checkbox("Show Whale Transactions Only (>10K XRP)")
    
    if dashboard.transactions:
        # Filter transactions
        filtered_transactions = list(dashboard.transactions)
        if show_whales_only:
            filtered_transactions = [tx for tx in filtered_transactions if tx['is_whale']]
        
        # Display transactions
        for tx in reversed(filtered_transactions[-20:]):  # Show last 20
            with st.container():
                col_type, col_details, col_amount = st.columns([1, 2, 1])
                
                with col_type:
                    whale_badge = "🐋" if tx['is_whale'] else ""
                    st.write(f"{whale_badge} {tx['type']}")
                
                with col_details:
                    from_addr = tx['account'] if tx['account'] else "N/A"
                    to_addr = tx['destination'] if tx['destination'] else "N/A"
                    st.write(f"From: {from_addr} → To: {to_addr}")
                    st.caption(f"Result: {tx['result']} | {tx['timestamp'].strftime('%H:%M:%S')}")
                
                with col_amount:
                    if tx['amount'] > 0:
                        st.write(f"{tx['amount']:,.0f} XRP")
                    else:
                        st.write("-")
                
                st.divider()
    else:
        st.info("Connect to XRPL to start monitoring transactions...")

# Sidebar content
with col2:
    # Account Lookup
    st.subheader("🔍 Account Lookup")
    account_address = st.text_input("Enter XRP Address", placeholder="rXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
    
    if st.button("Look Up Account") and account_address:
        with st.spinner("Fetching account information..."):
            account_info = dashboard.get_account_info(account_address)
            if account_info:
                st.success("Account found!")
                st.metric("Balance", f"{account_info['balance']:,.2f} XRP")
                st.metric("Sequence", account_info['sequence'])
            else:
                st.error("Account not found or error occurred")
    
    st.divider()
    
    # Whale Activity
    st.subheader("🐋 Recent Whale Activity")
    if dashboard.whale_transactions:
        for whale_tx in list(dashboard.whale_transactions)[-10:]:  # Show last 10
            st.write(f"💰 {whale_tx['amount']:,.0f} XRP")
            st.caption(f"{whale_tx['timestamp'].strftime('%H:%M:%S')} - {whale_tx['type']}")
            st.write("---")
    else:
        st.info("No whale transactions detected yet...")
    
    st.divider()
    
    # Transaction Volume Chart
    st.subheader("📊 Transaction Volume")
    if dashboard.transactions:
        # Create volume data for the last 10 minutes
        now = datetime.now()
        volume_data = []
        
        for i in range(10):
            time_slot = now - timedelta(minutes=i)
            slot_volume = sum(
                tx['amount'] for tx in dashboard.transactions 
                if time_slot - timedelta(minutes=1) <= tx['timestamp'] <= time_slot
            )
            volume_data.append({
                'time': time_slot.strftime('%H:%M'),
                'volume': slot_volume
            })
        
        volume_df = pd.DataFrame(volume_data)
        if not volume_df.empty:
            fig = px.bar(
                volume_df, 
                x='time', 
                y='volume',
                title="XRP Volume (Last 10 Minutes)",
                color_discrete_sequence=['#667eea']
            )
            fig.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("Built with Streamlit • Real-time data from XRPL WebSocket API")

# Auto-refresh logic
if auto_refresh and dashboard.connection_status == "Connected":
    time.sleep(refresh_rate)
    st.rerun()
