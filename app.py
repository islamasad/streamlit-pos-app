import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2.service_account import Credentials
from streamlit_option_menu import option_menu


# Initialize session state for data
if 'menu' not in st.session_state:
    st.session_state.menu = [
        {'id': 1, 'name': 'Fried Rice', 'price': 15000},
        {'id': 2, 'name': 'Fried Noodles', 'price': 12000},
        {'id': 3, 'name': 'Fried Chicken', 'price': 18000},
        {'id': 4, 'name': 'Iced Tea', 'price': 5000},
        {'id': 5, 'name': 'Orange Juice', 'price': 6000},
    ]
    
if 'transactions' not in st.session_state:
    st.session_state.transactions = []
    
if 'cart' not in st.session_state:
    st.session_state.cart = []

if 'amount_paid' not in st.session_state:
    st.session_state.amount_paid = 0

if 'payment_options' not in st.session_state:
    st.session_state.payment_options = []

# Google Sheets setup

SHEET_NAME = "POS_Transaction_Log"
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
@st.cache_resource(ttl=300)
def get_google_sheets_connection():
    try:
        # Check if secrets are available
        if 'gcp_service_account' not in st.secrets:
            st.error("Google Sheets credentials not found in secrets")
            return None
        
        # Get credentials from secrets
        sa_info = st.secrets["gcp_service_account"]
        
        # Clean private key
        private_key = sa_info['private_key']
        if '\\n' in private_key:
            private_key = private_key.replace('\\n', '\n')
        
        # Create credentials dictionary
        credentials_dict = {
            "type": sa_info["type"],
            "project_id": sa_info["project_id"],
            "private_key_id": sa_info["private_key_id"],
            "private_key": private_key,
            "client_email": sa_info["client_email"],
            "client_id": sa_info["client_id"],
            "auth_uri": sa_info["auth_uri"],
            "token_uri": sa_info["token_uri"],
            "auth_provider_x509_cert_url": sa_info["auth_provider_x509_cert_url"],
            "client_x509_cert_url": sa_info["client_x509_cert_url"]
        }
        
        # Create credentials
        creds = Credentials.from_service_account_info(
            credentials_dict,
            scopes=SCOPES
        )
        
        # Authorize gspread
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Google Sheets connection error: {str(e)}")
        return None
        
def get_sheet():
    try:
        client = get_google_sheets_connection()
        if not client:
            return None
        
        # Try to open existing sheet
        try:
            return client.open(SHEET_NAME).sheet1
        except gspread.SpreadsheetNotFound:
            # Create new spreadsheet
            spreadsheet = client.create(SHEET_NAME)
            
            # Share with service account
            sa_info = st.secrets["gcp_service_account"]
            spreadsheet.share(sa_info['client_email'], perm_type='user', role='writer')
            
            sheet = spreadsheet.sheet1
            
            # Add headers
            sheet.append_row([
                "Transaction ID", "Timestamp", "Total Amount", 
                "Option 1", "Option 2", "Option 3", 
                "Amount Paid", "Selected Option", "Items"
            ])
            
            return sheet
    except Exception as e:
        st.error(f"Failed to access sheet: {str(e)}")
        return None

def log_transaction(transaction_id, timestamp, total, options, amount_paid, selected_option, items):
    try:
        # Get sheet connection
        sheet = get_sheet()
        if not sheet:
            return False
            
        # Format items for logging
        items_str = "; ".join([f"{item['name']} x {item['qty']}" for item in items])
        
        # Determine selected option
        option_index = "Manual"
        if amount_paid in options:
            option_index = options.index(amount_paid) + 1
        
        # Add row to Google Sheet
        sheet.append_row([
            str(transaction_id),
            timestamp,
            str(total),
            str(options[0]),
            str(options[1]),
            str(options[2]),
            str(amount_paid),
            str(option_index),
            items_str
        ])
        
        return True
    except Exception as e:
        st.error(f"Failed to log transaction: {str(e)}")
        return False
    
# ENHANCED PAYMENT ALGORITHM WITH PRACTICAL OPTIONS
def payment_options(total):
    # Common Indonesian banknotes
    denominations = [1000, 2000, 5000, 10000, 20000, 50000, 100000]
    
    # Phase 1: Generate core options
    options = []
    
    # 1. Minimal convenient amount
    min_option = next((d for d in denominations if d >= total), total + 1000)
    options.append(min_option)
    
    # 2. Practical large denomination option
    if total <= 30000:
        large_option = 50000
    elif total <= 70000:
        large_option = 100000
    else:
        # Round up to next 50000
        large_option = ((total // 50000) + 1) * 50000
    options.append(large_option)
    
    # 3. Middle option - psychologically comfortable amount
    if total < 10000:
        # Round to nearest 500
        mid_option = round(total / 500) * 500
        if mid_option <= total:
            mid_option += 500
    elif total < 50000:
        # Round to nearest 5000
        mid_option = ((total // 5000) + 1) * 5000
    else:
        # Round to nearest 10000
        mid_option = ((total // 10000) + 1) * 10000
    options.append(mid_option)
    
    # Ensure all options are unique and sorted
    unique_options = sorted(set(options))
    
    # Fill in missing options if we don't have 3 distinct
    while len(unique_options) < 3:
        # Add a practical increment
        if total < 30000:
            new_option = unique_options[-1] + 5000
        else:
            new_option = unique_options[-1] + 10000
        unique_options.append(new_option)
    
    # Return exactly 3 options sorted ascending
    return sorted(unique_options[:3])

# POS Page with enhanced payment options
def pos_page():
    st.header("📊 Point of Sale")
    
    # Display menu in grid format
    st.subheader("Menu")
    cols = st.columns(4)
    
    for i, item in enumerate(st.session_state.menu):
        with cols[i % 4]:
            if st.button(f"{item['name']}\nRp {item['price']:,}", key=f"menu_{item['id']}"):
                # Check if item is already in cart
                existing_item = next((x for x in st.session_state.cart if x['id'] == item['id']), None)
                
                if existing_item:
                    existing_item['qty'] += 1
                else:
                    st.session_state.cart.append({
                        'id': item['id'],
                        'name': item['name'],
                        'price': item['price'],
                        'qty': 1
                    })
                st.success(f"{item['name']} added to cart!")
    
    st.divider()
    
    # Display shopping cart
    st.subheader("Shopping Cart")
    
    if not st.session_state.cart:
        st.info("Cart is empty. Please add items from the menu.")
    else:
        total_price = 0
        cart_df = []
        
        for item in st.session_state.cart:
            subtotal = item['price'] * item['qty']
            total_price += subtotal
            cart_df.append({
                'Item': item['name'],
                'Price': f"Rp {item['price']:,}",
                'Qty': item['qty'],
                'Subtotal': f"Rp {subtotal:,}"
            })
        
        st.dataframe(
            pd.DataFrame(cart_df),
            column_config={
                "Item": st.column_config.TextColumn("Item", width="medium"),
                "Price": st.column_config.TextColumn("Price", width="small"),
                "Qty": st.column_config.NumberColumn("Qty", width="small"),
                "Subtotal": st.column_config.TextColumn("Subtotal", width="medium")
            },
            hide_index=True,
            use_container_width=True
        )
        
        st.markdown(f"**Total Price: Rp {total_price:,}**")
        
        # Generate payment options
        options = payment_options(total_price)
        st.session_state.payment_options = options
        
        # Payment options section
        st.subheader("Payment Options")
        cols = st.columns(3)
        button_labels = ["Optimal Pay", "Smart Pay", "Easy Pay"]
        button_descriptions = [
            "Most efficient amount",
            "Comfortable amount",
            "Large denomination"
        ]
        
        for i, col in enumerate(cols):
            with col:
                if st.button(
                    f"{button_labels[i]}\nRp {options[i]:,}", 
                    key=f"option{i+1}", 
                    use_container_width=True,
                    help=button_descriptions[i]
                ):
                    st.session_state.amount_paid = options[i]
                    st.success(f"Amount set to Rp {options[i]:,}")
        
        # Manual input
        amount_paid = st.number_input(
            "Amount Paid", 
            min_value=total_price, 
            value=st.session_state.amount_paid or total_price,
            step=1000,
            format="%d"
        )
        
        change = amount_paid - total_price
        
        if change >= 0:
            st.success(f"Change: Rp {change:,}")
        else:
            st.error(f"Amount insufficient: Rp {-change:,}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Complete Transaction", type="primary", use_container_width=True):
                # Start transaction processing
                with st.spinner("Processing transaction..."):
                    # Save transaction locally
                    transaction_id = len(st.session_state.transactions) + 1
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    new_transaction = {
                        'id': transaction_id,
                        'time': timestamp,
                        'items': st.session_state.cart.copy(),
                        'total': total_price,
                        'amount_paid': amount_paid,
                        'change': change
                    }
                    
                    st.session_state.transactions.append(new_transaction)
                    
                    # Log to Google Sheets in background
                    try:
                        log_success = log_transaction(
                            transaction_id=transaction_id,
                            timestamp=timestamp,
                            total=total_price,
                            options=options,
                            amount_paid=amount_paid,
                            selected_option=st.session_state.amount_paid,
                            items=st.session_state.cart
                        )
                        
                        if log_success:
                            st.success("Transaction logged to Google Sheets")
                        else:
                            st.warning("Transaction saved locally but failed to log to Google Sheets")
                    except Exception as e:
                        st.error(f"Logging error: {str(e)}")
                    
                    # Reset cart
                    st.session_state.cart = []
                    st.session_state.amount_paid = 0
                    st.success("Transaction completed successfully!")
        with col2:
            if st.button("Clear Cart", use_container_width=True):
                st.session_state.cart = []
                st.session_state.amount_paid = 0
                st.info("Cart has been cleared")
        with col3:
            if st.button("Remove All", use_container_width=True, type="secondary"):
                st.session_state.cart = []
                st.session_state.amount_paid = 0
                st.info("All items removed")

# Menu Management Page (unchanged)
def menu_page():
    st.header("🍔 Menu Management")
    
    # Form to add new menu item
    with st.form(key='menu_form', clear_on_submit=True):
        st.subheader("Add New Menu Item")
        name = st.text_input("Item Name")
        price = st.number_input("Price", min_value=1000, step=1000)
        
        if st.form_submit_button("Add Item", type="primary"):
            if name and price:
                # Check if item already exists
                if any(item['name'].lower() == name.lower() for item in st.session_state.menu):
                    st.error("Item already exists!")
                else:
                    new_id = max(item['id'] for item in st.session_state.menu) + 1
                    st.session_state.menu.append({
                        'id': new_id,
                        'name': name,
                        'price': price
                    })
                    st.success(f"{name} added to menu!")
            else:
                st.error("Name and price are required!")
    
    st.divider()
    
    # Menu list table
    st.subheader("Menu List")
    if not st.session_state.menu:
        st.info("No menu items available")
    else:
        menu_df = []
        for item in st.session_state.menu:
            menu_df.append({
                'ID': item['id'],
                'Name': item['name'],
                'Price': f"Rp {item['price']:,}"
            })
        
        df = pd.DataFrame(menu_df)
        st.dataframe(
            df,
            column_config={
                "ID": st.column_config.NumberColumn("ID", width="small"),
                "Name": st.column_config.TextColumn("Item Name", width="medium"),
                "Price": st.column_config.TextColumn("Price", width="medium")
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Delete menu item
        st.subheader("Delete Menu Item")
        menu_options = [f"{item['id']} - {item['name']} (Rp {item['price']:,})" for item in st.session_state.menu]
        delete_menu = st.selectbox("Select item to delete", menu_options)
        
        if st.button("Delete Item", type="secondary"):
            menu_id = int(delete_menu.split(" - ")[0])
            st.session_state.menu = [item for item in st.session_state.menu if item['id'] != menu_id]
            st.success("Item deleted successfully!")

# Transactions Page (unchanged)
def transactions_page():
    st.header("📋 Transaction History")
    
    if not st.session_state.transactions:
        st.info("No transactions recorded")
    else:
        # Transaction summary
        total_transactions = len(st.session_state.transactions)
        total_revenue = sum(t['total'] for t in st.session_state.transactions)
        
        col1, col2 = st.columns(2)
        col1.metric("Total Transactions", total_transactions)
        col2.metric("Total Revenue", f"Rp {total_revenue:,}")
        
        st.divider()
        
        # Transactions table
        transactions_df = []
        for t in st.session_state.transactions:
            transactions_df.append({
                'ID': t['id'],
                'Time': t['time'],
                'Items': sum(item['qty'] for item in t['items']),
                'Total': f"Rp {t['total']:,}",
                'Paid': f"Rp {t['amount_paid']:,}",
                'Change': f"Rp {t['change']:,}"
            })
        
        st.dataframe(
            pd.DataFrame(transactions_df),
            column_config={
                "ID": st.column_config.NumberColumn("ID", width="small"),
                "Time": st.column_config.DatetimeColumn("Time", format="YYYY-MM-DD HH:mm:ss"),
                "Items": st.column_config.NumberColumn("Items", width="small"),
                "Total": st.column_config.TextColumn("Total", width="medium"),
                "Paid": st.column_config.TextColumn("Paid", width="medium"),
                "Change": st.column_config.TextColumn("Change", width="medium")
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Transaction details
        st.divider()
        st.subheader("Transaction Details")
        transaction_options = [f"{t['id']} - {t['time']} (Rp {t['total']:,})" for t in st.session_state.transactions]
        selected_transaction = st.selectbox("Select transaction to view details", transaction_options)
        
        if selected_transaction:
            transaction_id = int(selected_transaction.split(" - ")[0])
            transaction = next(t for t in st.session_state.transactions if t['id'] == transaction_id)
            
            st.markdown(f"**Transaction ID:** {transaction['id']}")
            st.markdown(f"**Time:** {transaction['time']}")
            st.markdown(f"**Total:** Rp {transaction['total']:,}")
            st.markdown(f"**Paid:** Rp {transaction['amount_paid']:,}")
            st.markdown(f"**Change:** Rp {transaction['change']:,}")
            
            st.subheader("Items Purchased")
            item_df = []
            for item in transaction['items']:
                item_df.append({
                    'Item': item['name'],
                    'Unit Price': f"Rp {item['price']:,}",
                    'Qty': item['qty'],
                    'Subtotal': f"Rp {item['price'] * item['qty']:,}"
                })
            
            st.dataframe(
                pd.DataFrame(item_df),
                column_config={
                    "Item": st.column_config.TextColumn("Item", width="medium"),
                    "Unit Price": st.column_config.TextColumn("Unit Price", width="medium"),
                    "Qty": st.column_config.NumberColumn("Qty", width="small"),
                    "Subtotal": st.column_config.TextColumn("Subtotal", width="medium")
                },
                hide_index=True,
                use_container_width=True
            )

# Page configuration
st.set_page_config(
    page_title="POS System",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar navigation
with st.sidebar:
    st.title("🛒 POS System")
    selected = option_menu(
        menu_title=None,
        options=["POS", "Menu", "Transactions"],
        icons=["cash-coin", "book", "clock-history"],
        default_index=0
    )
    
    st.divider()
    st.caption("Version 1.0 | © 2025 MZAIUE")
    
    # Google Sheets status - only shown when requested
    if st.button("Check Google Sheets Status"):
        try:
            client = get_google_sheets_connection()
            if client:
                try:
                    spreadsheets = client.list_spreadsheet_files()
                    st.success("Google Sheets connected")
                    st.info(f"Found {len(spreadsheets)} spreadsheets")
                    
                    # Check if our sheet exists
                    found = any(s['name'] == SHEET_NAME for s in spreadsheets)
                    if found:
                        st.success(f"Spreadsheet '{SHEET_NAME}' exists")
                        try:
                            sheet = get_sheet()
                            records = sheet.get_all_records()
                            st.info(f"{len(records)} transactions logged")
                        except:
                            st.info("Sheet is empty")
                    else:
                        st.warning(f"Spreadsheet '{SHEET_NAME}' not found")
                except Exception as e:
                    st.error(f"Connection error: {str(e)}")
            else:
                st.error("Failed to connect to Google Sheets")
        except Exception as e:
            st.error(f"Error: {str(e)}")

# Display selected page
if selected == "POS":
    pos_page()
elif selected == "Menu":
    menu_page()
elif selected == "Transactions":
    transactions_page()