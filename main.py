import os
import json
import asyncio
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', '7995053218:AAHjjk02qRGrVmrGy-i-xL4vXio7m8bwaE0')
OWNER_ID = int(os.getenv('OWNER_ID', '1735522859'))

class TelegramBot:
    def __init__(self):
        self.admin_states = {}
        self.user_states = {}
        self.init_data_files()
    
    def init_data_files(self):
        """Initialize JSON data files"""
        files = {
            'data/users.json': {},
            'data/items.json': {},
            'data/orders.json': [],
            'data/coupons.json': {}
        }
        
        os.makedirs('data', exist_ok=True)
        
        for filepath, default_data in files.items():
            if not os.path.exists(filepath):
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(default_data, f, ensure_ascii=False, indent=2)
    
    def load_json(self, filepath):
        """Load JSON data"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def save_json(self, filepath, data):
        """Save JSON data"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id == OWNER_ID
    
    def get_user_keyboard(self):
        """Get user keyboard"""
        keyboard = [
            [KeyboardButton("🛍️ Browse Items"), KeyboardButton("💰 My Balance")],
            [KeyboardButton("📦 My Orders")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    def get_admin_keyboard(self):
        """Get admin keyboard - Updated Menu"""
        keyboard = [
            [KeyboardButton("➕ Add Item"), KeyboardButton("🧭 Manage Item")],
            [KeyboardButton("👤 View Users"), KeyboardButton("💰 Manage Coins")],
            [KeyboardButton("📦 View Orders"), KeyboardButton("🏷️ Add Coupon")],
            [KeyboardButton("🧭 Manage Coupon")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "User"
        
        welcome_text = f"🎮 Welcome to @{username}\n\n🏪Osamu Gaming Items Store!🏪\n\nSelect an option:"
        
        if self.is_admin(user_id):
            await update.message.reply_text(
                welcome_text,
                reply_markup=self.get_admin_keyboard()
            )
        else:
            await update.message.reply_text(
                welcome_text,
                reply_markup=self.get_user_keyboard()
            )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        user_id = update.effective_user.id
        username = update.effective_user.username or f"user_{user_id}"
        text = update.message.text
        
        # Register user if not exists
        users = self.load_json('data/users.json')
        if str(user_id) not in users:
            users[str(user_id)] = {
                'username': username,
                'coins': 0,
                'registered_at': datetime.now().isoformat()
            }
            self.save_json('data/users.json', users)
        
        if self.is_admin(user_id):
            await self.handle_admin_messages(update, context, text)
        else:
            await self.handle_user_messages(update, context, text)
    
    async def handle_admin_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Handle admin messages"""
        user_id = update.effective_user.id
        
        # Check if admin is in a state (adding item, coupon, etc.)
        if user_id in self.admin_states:
            await self.handle_admin_states(update, context)
            return
        
        # Handle admin buttons
        if text == "➕ Add Item":
            self.admin_states[user_id] = {'action': 'add_item', 'step': 'category'}
            await update.message.reply_text("📝 Enter category (e.g., MLBB, PUBG):")
        
        elif text == "🧭 Manage Item":
            items = self.load_json('data/items.json')
            if not items:
                await update.message.reply_text("❌ No items found!")
                return
            
            keyboard = []
            for item_id, item in items.items():
                keyboard.append([InlineKeyboardButton(
                    f"{item['name']} - {item['price']} MMK", 
                    callback_data=f"manage_item_{item_id}"
                )])
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_admin")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("🧭 Select item to manage:", reply_markup=reply_markup)
        
        elif text == "👤 View Users":
            users = self.load_json('data/users.json')
            if not users:
                await update.message.reply_text("❌ No users found!")
                return
            
            keyboard = []
            for user_id_str, user in users.items():
                keyboard.append([InlineKeyboardButton(
                    f"@{user['username']} - {user['coins']} MMK", 
                    callback_data=f"manage_user_{user_id_str}"
                )])
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_admin")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("👤 Users List:", reply_markup=reply_markup)
        
        elif text == "💰 Manage Coins":
            users = self.load_json('data/users.json')
            if not users:
                await update.message.reply_text("❌ No users found!")
                return
            
            keyboard = []
            for user_id_str, user in users.items():
                keyboard.append([InlineKeyboardButton(
                    f"@{user['username']} - {user['coins']} MMK", 
                    callback_data=f"coins_user_{user_id_str}"
                )])
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_admin")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("💰 Select user to manage coins:", reply_markup=reply_markup)
        
        elif text == "📦 View Orders":
            orders = self.load_json('data/orders.json')
            pending_orders = [order for order in orders if order.get('status') == 'pending']
            
            if not pending_orders:
                await update.message.reply_text("✅ No pending orders!")
                return
            
            keyboard = []
            for order in pending_orders:
                items = self.load_json('data/items.json')
                item = items.get(order['item_id'], {})
                users = self.load_json('data/users.json')
                user = users.get(str(order['user_id']), {})
                
                keyboard.append([InlineKeyboardButton(
                    f"@{user.get('username', 'Unknown')} - {item.get('name', 'Unknown')} - {order.get('total_price', 0)} MMK", 
                    callback_data=f"order_detail_{order['order_id']}"
                )])
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_admin")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("📦 Pending Orders:", reply_markup=reply_markup)
        
        elif text == "🏷️ Add Coupon":
            self.admin_states[user_id] = {'action': 'add_coupon', 'step': 'code'}
            await update.message.reply_text("🏷️ Enter coupon code (e.g., NEWYEAR):")
        
        elif text == "🧭 Manage Coupon":
            coupons = self.load_json('data/coupons.json')
            if not coupons:
                await update.message.reply_text("❌ No coupons found!")
                return
            
            keyboard = []
            for code, coupon in coupons.items():
                keyboard.append([InlineKeyboardButton(
                    f"{code} - {coupon['discount']} MMK", 
                    callback_data=f"manage_coupon_{code}"
                )])
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_admin")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("🧭 Select coupon to manage:", reply_markup=reply_markup)
        
        else:
            await update.message.reply_text("Please use the menu buttons or type /start")
    
    async def handle_user_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Handle user messages"""
        user_id = update.effective_user.id
        
        # Check if user is in a state (applying coupon, etc.)
        if user_id in self.user_states:
            await self.handle_user_states(update, context)
            return
        
        # Handle user buttons
        if text == "🛍️ Browse Items":
            items = self.load_json('data/items.json')
            if not items:
                await update.message.reply_text("❌ No items available!")
                return
            
            # Group items by category
            categories = {}
            for item_id, item in items.items():
                category = item['category']
                if category not in categories:
                    categories[category] = []
                categories[category].append((item_id, item))
            
            keyboard = []
            for category in categories:
                keyboard.append([InlineKeyboardButton(
                    f"🎮 {category}", 
                    callback_data=f"category_{category}"
                )])
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_user")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("🛍️ Select category:", reply_markup=reply_markup)
        
        elif text == "💰 My Balance":
            users = self.load_json('data/users.json')
            user = users.get(str(user_id), {})
            balance = user.get('coins', 0)
            await update.message.reply_text(f"💳 Your Balance: {balance} MMK")
        
        elif text == "📦 My Orders":
            orders = self.load_json('data/orders.json')
            user_orders = [order for order in orders if order['user_id'] == user_id]
            
            if not user_orders:
                await update.message.reply_text("📦 You have no orders yet.")
                return
            
            message = "📦 Your Orders:\n\n"
            for order in user_orders[-10:]:  # Show last 10 orders
                items = self.load_json('data/items.json')
                item = items.get(order['item_id'], {})
                status_emoji = "✅" if order['status'] == 'confirmed' else "⏳" if order['status'] == 'pending' else "❌"
                message += f"{status_emoji} {item.get('name', 'Unknown')} - {order.get('total_price', 0)} MMK\n"
            
            await update.message.reply_text(message)
        
        else:
            await update.message.reply_text("Please use the menu buttons or type /start")
    
    async def handle_admin_states(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle admin multi-step processes"""
        user_id = update.effective_user.id
        state = self.admin_states[user_id]
        text = update.message.text.strip()
        
        if state['action'] == 'add_item':
            if state['step'] == 'category':
                state['category'] = text
                state['step'] = 'name'
                await update.message.reply_text("📝 Enter item name:")
            
            elif state['step'] == 'name':
                state['name'] = text
                state['step'] = 'price'
                await update.message.reply_text("📝 Enter price (MMK):")
            
            elif state['step'] == 'price':
                try:
                    price = int(text)
                    if price <= 0:
                        raise ValueError
                    state['price'] = price
                    state['step'] = 'stock'
                    await update.message.reply_text("📝 Enter stock count:")
                except ValueError:
                    await update.message.reply_text("❌ Invalid price. Please enter a positive number:")
            
            elif state['step'] == 'stock':
                try:
                    stock = int(text)
                    if stock < 0:
                        raise ValueError
                    
                    # Save item
                    items = self.load_json('data/items.json')
                    item_id = f"item_{len(items) + 1}"
                    
                    items[item_id] = {
                        'category': state['category'],
                        'name': state['name'],
                        'price': state['price'],
                        'stock': stock,
                        'created_at': datetime.now().isoformat()
                    }
                    
                    self.save_json('data/items.json', items)
                    
                    await update.message.reply_text(
                        f"✅ Item Added!\n\n"
                        f"Category: {state['category']}\n"
                        f"Name: {state['name']}\n"
                        f"Price: {state['price']} MMK\n"
                        f"Stock: {stock}"
                    )
                    
                    del self.admin_states[user_id]
                    
                except ValueError:
                    await update.message.reply_text("❌ Invalid stock. Please enter a valid number:")
        
        elif state['action'] == 'add_coupon':
            if state['step'] == 'code':
                state['code'] = text.upper()
                state['step'] = 'discount'
                await update.message.reply_text("📝 Enter discount amount (MMK):")
            
            elif state['step'] == 'discount':
                try:
                    discount = int(text)
                    if discount <= 0:
                        raise ValueError
                    
                    # Save coupon
                    coupons = self.load_json('data/coupons.json')
                    coupons[state['code']] = {
                        'discount': discount,
                        'created_at': datetime.now().isoformat()
                    }
                    
                    self.save_json('data/coupons.json', coupons)
                    
                    await update.message.reply_text(
                        f"🏷️ Coupon \"{state['code']}\" saved - {discount} MMK discount"
                    )
                    
                    del self.admin_states[user_id]
                    
                except ValueError:
                    await update.message.reply_text("❌ Invalid discount. Please enter a positive number:")
        
        elif state['action'] == 'manage_coins':
            try:
                amount = int(text)
                if amount <= 0:
                    raise ValueError
                
                users = self.load_json('data/users.json')
                target_user_id = state['user_id']
                
                if state['operation'] == 'add':
                    users[target_user_id]['coins'] += amount
                    operation_text = "added"
                else:  # remove
                    users[target_user_id]['coins'] = max(0, users[target_user_id]['coins'] - amount)
                    operation_text = "removed"
                
                self.save_json('data/users.json', users)
                
                await update.message.reply_text(
                    f"✅ Coin updated!\n"
                    f"@{users[target_user_id]['username']} now has {users[target_user_id]['coins']} MMK"
                )
                
                del self.admin_states[user_id]
                
            except ValueError:
                await update.message.reply_text("❌ Invalid amount. Please enter a positive number:")
        
        elif state['action'] == 'edit_item_price':
            try:
                new_price = int(text)
                if new_price <= 0:
                    raise ValueError
                
                items = self.load_json('data/items.json')
                item_id = state['item_id']
                
                if item_id in items:
                    old_price = items[item_id]['price']
                    items[item_id]['price'] = new_price
                    self.save_json('data/items.json', items)
                    
                    await update.message.reply_text(
                        f"✅ Price updated!\n\n"
                        f"📱 {items[item_id]['name']}\n"
                        f"💰 Old Price: {old_price} MMK\n"
                        f"💰 New Price: {new_price} MMK"
                    )
                else:
                    await update.message.reply_text("❌ Item not found!")
                
                del self.admin_states[user_id]
                
            except ValueError:
                await update.message.reply_text("❌ Invalid price. Please enter a positive number:")
        
        elif state['action'] == 'edit_item_stock':
            try:
                new_stock = int(text)
                if new_stock < 0:
                    raise ValueError
                
                items = self.load_json('data/items.json')
                item_id = state['item_id']
                
                if item_id in items:
                    old_stock = items[item_id]['stock']
                    items[item_id]['stock'] = new_stock
                    self.save_json('data/items.json', items)
                    
                    await update.message.reply_text(
                        f"✅ Stock updated!\n\n"
                        f"📱 {items[item_id]['name']}\n"
                        f"📦 Old Stock: {old_stock}\n"
                        f"📦 New Stock: {new_stock}"
                    )
                else:
                    await update.message.reply_text("❌ Item not found!")
                
                del self.admin_states[user_id]
                
            except ValueError:
                await update.message.reply_text("❌ Invalid stock. Please enter a valid number (0 or more):")
        
        elif state['action'] == 'edit_coupon_discount':
            try:
                new_discount = int(text)
                if new_discount <= 0:
                    raise ValueError
                
                coupons = self.load_json('data/coupons.json')
                coupon_code = state['coupon_code']
                
                if coupon_code in coupons:
                    old_discount = coupons[coupon_code]['discount']
                    coupons[coupon_code]['discount'] = new_discount
                    self.save_json('data/coupons.json', coupons)
                    
                    await update.message.reply_text(
                        f"✅ Coupon updated!\n\n"
                        f"🏷️ Code: {coupon_code}\n"
                        f"💰 Old Discount: {old_discount} MMK\n"
                        f"💰 New Discount: {new_discount} MMK"
                    )
                else:
                    await update.message.reply_text("❌ Coupon not found!")
                
                del self.admin_states[user_id]
                
            except ValueError:
                await update.message.reply_text("❌ Invalid discount. Please enter a positive number:")
    
    async def handle_user_states(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle user multi-step processes"""
        user_id = update.effective_user.id
        state = self.user_states[user_id]
        text = update.message.text.strip().upper()
        
        if state['action'] == 'apply_coupon':
            coupons = self.load_json('data/coupons.json')
            
            if text in coupons:
                item_id = state['item_id']
                discount = coupons[text]['discount']
                
                # Process purchase with coupon
                await self.process_purchase(update, context, item_id, discount)
                del self.user_states[user_id]
            else:
                await update.message.reply_text("❌ Invalid coupon code. Try again or type 'skip':")
    
    async def process_purchase(self, update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: str, coupon_discount: int = 0):
        """Process purchase"""
        user_id = update.effective_user.id
        
        # Load data
        items = self.load_json('data/items.json')
        users = self.load_json('data/users.json')
        orders = self.load_json('data/orders.json')
        
        item = items.get(item_id)
        user = users.get(str(user_id))
        
        if not item or not user:
            await update.message.reply_text("❌ Error processing purchase!")
            return
        
        if item['stock'] <= 0:
            await update.message.reply_text("❌ Item out of stock!")
            return
        
        total_price = max(0, item['price'] - coupon_discount)
        
        if user['coins'] < total_price:
            await update.message.reply_text(f"❌ Insufficient balance! You need {total_price} MMK but have {user['coins']} MMK")
            return
        
        # Create order
        order_id = f"order_{len(orders) + 1}"
        order = {
            'order_id': order_id,
            'user_id': user_id,
            'item_id': item_id,
            'total_price': total_price,
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }
        
        # Deduct coins and reduce stock
        users[str(user_id)]['coins'] -= total_price
        items[item_id]['stock'] -= 1
        orders.append(order)
        
        # Save data
        self.save_json('data/users.json', users)
        self.save_json('data/items.json', items)
        self.save_json('data/orders.json', orders)
        
        await update.message.reply_text(
            f"✅ Order placed successfully!\n\n"
            f"Item: {item['name']}\n"
            f"Price: {total_price} MMK\n"
            f"Order ID: {order_id}\n"
            f"Status: Pending confirmation"
        )
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        
        if data.startswith("manage_item_"):
            item_id = data.replace("manage_item_", "")
            items = self.load_json('data/items.json')
            item = items.get(item_id)
            
            if item:
                keyboard = [
                    [InlineKeyboardButton("📝 Edit Price", callback_data=f"edit_price_{item_id}")],
                    [InlineKeyboardButton("📦 Edit Stock", callback_data=f"edit_stock_{item_id}")],
                    [InlineKeyboardButton("🗑️ Delete Item", callback_data=f"delete_item_{item_id}")],
                    [InlineKeyboardButton("🔙 Back", callback_data="back_admin")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"🧭 Managing: {item['name']}\n"
                    f"Category: {item['category']}\n"
                    f"Price: {item['price']} MMK\n"
                    f"Stock: {item['stock']}\n\n"
                    f"Select action:",
                    reply_markup=reply_markup
                )
        
        elif data.startswith("coins_user_"):
            user_id_str = data.replace("coins_user_", "")
            users = self.load_json('data/users.json')
            user = users.get(user_id_str)
            
            if user:
                keyboard = [
                    [InlineKeyboardButton("➕ Add Coins", callback_data=f"add_coins_{user_id_str}")],
                    [InlineKeyboardButton("➖ Remove Coins", callback_data=f"remove_coins_{user_id_str}")],
                    [InlineKeyboardButton("🔙 Back", callback_data="back_admin")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"💰 Manage Coins for @{user['username']}\n"
                    f"Current Balance: {user['coins']} MMK\n\n"
                    f"Select action:",
                    reply_markup=reply_markup
                )
        
        elif data.startswith("add_coins_") or data.startswith("remove_coins_"):
            operation = "add" if data.startswith("add_coins_") else "remove"
            user_id_str = data.replace(f"{operation}_coins_", "")
            
            self.admin_states[user_id] = {
                'action': 'manage_coins',
                'operation': operation,
                'user_id': user_id_str
            }
            
            await query.edit_message_text(f"Enter amount to {operation}:")
        
        elif data.startswith("order_detail_"):
            order_id = data.replace("order_detail_", "")
            orders = self.load_json('data/orders.json')
            
            order = next((o for o in orders if o['order_id'] == order_id), None)
            if order:
                items = self.load_json('data/items.json')
                users = self.load_json('data/users.json')
                item = items.get(order['item_id'], {})
                user = users.get(str(order['user_id']), {})
                
                keyboard = [
                    [InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_order_{order_id}")],
                    [InlineKeyboardButton("❌ Reject", callback_data=f"reject_order_{order_id}")],
                    [InlineKeyboardButton("🔙 Back", callback_data="back_admin")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"📦 Order Details\n\n"
                    f"Order ID: {order_id}\n"
                    f"User: @{user.get('username', 'Unknown')}\n"
                    f"Item: {item.get('name', 'Unknown')}\n"
                    f"Price: {order.get('total_price', 0)} MMK\n"
                    f"Status: {order.get('status', 'Unknown')}\n\n"
                    f"Select action:",
                    reply_markup=reply_markup
                )
        
        elif data.startswith("confirm_order_") or data.startswith("reject_order_"):
            action = "confirmed" if data.startswith("confirm_order_") else "rejected"
            order_id = data.replace(f"{action.split('ed')[0]}_order_", "")
            
            orders = self.load_json('data/orders.json')
            
            for order in orders:
                if order['order_id'] == order_id:
                    order['status'] = action
                    break
            
            self.save_json('data/orders.json', orders)
            
            await query.edit_message_text(f"✅ Order {order_id} has been {action}!")
        
        # Add more callback handlers for user side (Browse Items, Buy, etc.)
        elif data.startswith("category_"):
            category = data.replace("category_", "")
            items = self.load_json('data/items.json')
            
            # Filter items by category
            category_items = {k: v for k, v in items.items() if v['category'] == category}
            
            keyboard = []
            for item_id, item in category_items.items():
                stock_text = f"(Stock: {item['stock']})" if item['stock'] > 0 else "(Out of Stock)"
                keyboard.append([InlineKeyboardButton(
                    f"{item['name']} - {item['price']} MMK {stock_text}", 
                    callback_data=f"item_{item_id}"
                )])
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_user")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"🎮 {category} Items:", reply_markup=reply_markup)
        
        elif data.startswith("item_"):
            item_id = data.replace("item_", "")
            items = self.load_json('data/items.json')
            item = items.get(item_id)
            
            if item:
                keyboard = []
                if item['stock'] > 0:
                    keyboard.append([InlineKeyboardButton("💳 Buy Now", callback_data=f"buy_{item_id}")])
                    keyboard.append([InlineKeyboardButton("🏷️ Use Coupon", callback_data=f"coupon_{item_id}")])
                keyboard.append([InlineKeyboardButton("🔙 Back", callback_data=f"category_{item['category']}")])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"🎮 {item['name']}\n\n"
                    f"💰 Price: {item['price']} MMK\n"
                    f"📦 Stock: {item['stock']}\n"
                    f"🏷️ Category: {item['category']}\n\n"
                    f"{'✅ Available' if item['stock'] > 0 else '❌ Out of Stock'}",
                    reply_markup=reply_markup
                )
        
        elif data.startswith("buy_"):
            item_id = data.replace("buy_", "")
            await self.process_purchase(update, context, item_id)
            await query.edit_message_text("🔄 Processing your order...")
        
        elif data.startswith("coupon_"):
            item_id = data.replace("coupon_", "")
            self.user_states[user_id] = {
                'action': 'apply_coupon',
                'item_id': item_id
            }
            await query.edit_message_text("🏷️ Enter coupon code (or type 'skip' to buy without coupon):")
        
        # Admin-specific callback handlers for managing items
        elif data.startswith("edit_price_"):
            item_id = data.replace("edit_price_", "")
            self.admin_states[user_id] = {
                'action': 'edit_item_price',
                'item_id': item_id
            }
            await query.edit_message_text("📝 Enter new price (MMK):")
        
        elif data.startswith("edit_stock_"):
            item_id = data.replace("edit_stock_", "")
            self.admin_states[user_id] = {
                'action': 'edit_item_stock',
                'item_id': item_id
            }
            await query.edit_message_text("📝 Enter new stock quantity:")
        
        elif data.startswith("delete_item_"):
            item_id = data.replace("delete_item_", "")
            items = self.load_json('data/items.json')
            item = items.get(item_id)
            
            if item:
                keyboard = [
                    [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete_item_{item_id}")],
                    [InlineKeyboardButton("❌ Cancel", callback_data=f"manage_item_{item_id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"🗑️ Are you sure you want to delete:\n\n"
                    f"📱 {item['name']}\n"
                    f"💰 {item['price']} MMK\n"
                    f"📦 Stock: {item['stock']}\n\n"
                    f"This action cannot be undone!",
                    reply_markup=reply_markup
                )
        
        elif data.startswith("confirm_delete_item_"):
            item_id = data.replace("confirm_delete_item_", "")
            items = self.load_json('data/items.json')
            
            if item_id in items:
                item_name = items[item_id]['name']
                del items[item_id]
                self.save_json('data/items.json', items)
                
                await query.edit_message_text(f"✅ Item '{item_name}' has been deleted successfully!")
            else:
                await query.edit_message_text("❌ Item not found!")
        
        # Admin-specific callback handlers for managing coupons
        elif data.startswith("manage_coupon_"):
            coupon_code = data.replace("manage_coupon_", "")
            coupons = self.load_json('data/coupons.json')
            coupon = coupons.get(coupon_code)
            
            if coupon:
                keyboard = [
                    [InlineKeyboardButton("📝 Edit Discount", callback_data=f"edit_coupon_{coupon_code}")],
                    [InlineKeyboardButton("🗑️ Delete Coupon", callback_data=f"delete_coupon_{coupon_code}")],
                    [InlineKeyboardButton("🔙 Back", callback_data="back_admin")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"🧭 Managing Coupon: {coupon_code}\n"
                    f"💰 Discount: {coupon['discount']} MMK\n\n"
                    f"Select action:",
                    reply_markup=reply_markup
                )
        
        elif data.startswith("edit_coupon_"):
            coupon_code = data.replace("edit_coupon_", "")
            self.admin_states[user_id] = {
                'action': 'edit_coupon_discount',
                'coupon_code': coupon_code
            }
            await query.edit_message_text("📝 Enter new discount amount (MMK):")
        
        elif data.startswith("delete_coupon_"):
            coupon_code = data.replace("delete_coupon_", "")
            coupons = self.load_json('data/coupons.json')
            coupon = coupons.get(coupon_code)
            
            if coupon:
                keyboard = [
                    [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete_coupon_{coupon_code}")],
                    [InlineKeyboardButton("❌ Cancel", callback_data=f"manage_coupon_{coupon_code}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"🗑️ Are you sure you want to delete coupon:\n\n"
                    f"🏷️ Code: {coupon_code}\n"
                    f"💰 Discount: {coupon['discount']} MMK\n\n"
                    f"This action cannot be undone!",
                    reply_markup=reply_markup
                )
        
        elif data.startswith("confirm_delete_coupon_"):
            coupon_code = data.replace("confirm_delete_coupon_", "")
            coupons = self.load_json('data/coupons.json')
            
            if coupon_code in coupons:
                del coupons[coupon_code]
                self.save_json('data/coupons.json', coupons)
                
                await query.edit_message_text(f"✅ Coupon '{coupon_code}' has been deleted successfully!")
            else:
                await query.edit_message_text("❌ Coupon not found!")
        
        # Handle Back buttons
        elif data == "back_admin":
            await query.edit_message_text("🔙 Returned to main menu. Use the keyboard buttons below.")
        
        elif data == "back_user":
            await query.edit_message_text("🔙 Returned to main menu. Use the keyboard buttons below.")
        
        # Handle category back navigation for users
        elif data.startswith("category_") and not data.startswith("category_back_"):
            # This is handled above in the category selection
            pass
    
    def run(self):
        """Start the bot"""
        print("Bot starting...")
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        application.add_handler(CallbackQueryHandler(self.handle_callback_query))
        
        # Start the bot
        application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    bot = TelegramBot()
    bot.run()