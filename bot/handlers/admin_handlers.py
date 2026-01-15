from telegram import Update
from telegram.ext import ContextTypes
from bot.keyboards import Keyboards
from bot.database import Database
from bot.utils import format_price, format_user_mention, validate_positive_integer, format_order_status

class AdminHandlers:
    def __init__(self, database: Database):
        self.db = database
        self.keyboards = Keyboards()
        self.admin_states = {}  # Track admin states for multi-step flows
    
    async def show_admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main admin menu"""
        text = "🔧 Admin Panel\n\nSelect an option:"
        
        if update.callback_query:
            await update.callback_query.message.reply_text(
                text=text,
                reply_markup=self.keyboards.admin_main_menu()
            )
        else:
            await update.message.reply_text(
                text=text,
                reply_markup=self.keyboards.admin_main_menu()
            )
    
    async def start_add_item_flow(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the add item flow"""
        admin_id = update.effective_user.id
        self.admin_states[admin_id] = {
            'action': 'add_item_category',
            'item_data': {}
        }
        
        await update.callback_query.edit_message_text(
            text="➕ Adding New Item\n\nEnter category (e.g., MLBB, PUBG):",
            reply_markup=self.keyboards.back_button()
        )
    
    async def handle_add_item_steps(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle multi-step item addition"""
        admin_id = update.effective_user.id
        text = update.message.text.strip()
        
        if admin_id not in self.admin_states:
            return
        
        state = self.admin_states[admin_id]
        
        if state['action'] == 'add_item_category':
            state['item_data']['category'] = text.upper()
            state['action'] = 'add_item_name'
            await update.message.reply_text("Enter item name:")
            
        elif state['action'] == 'add_item_name':
            state['item_data']['name'] = text
            state['action'] = 'add_item_price'
            await update.message.reply_text("Enter price (MMK):")
            
        elif state['action'] == 'add_item_price':
            price = validate_positive_integer(text)
            if price:
                state['item_data']['price'] = price
                state['action'] = 'add_item_stock'
                await update.message.reply_text("Enter stock count:")
            else:
                await update.message.reply_text("❌ Invalid price. Please enter a positive number:")
                
        elif state['action'] == 'add_item_stock':
            stock = validate_positive_integer(text)
            if stock:
                # Save item
                item_data = state['item_data']
                item_id = self.db.add_item(
                    item_data['category'],
                    item_data['name'],
                    item_data['price'],
                    stock
                )
                
                confirmation_text = f"""✅ Item Added!

Category: {item_data['category']}
Name: {item_data['name']}
Price: {format_price(item_data['price'])}
Stock: {stock}
Item ID: {item_id}"""
                
                await update.message.reply_text(
                    confirmation_text,
                    reply_markup=self.keyboards.back_button()
                )
                
                # Clear state
                del self.admin_states[admin_id]
            else:
                await update.message.reply_text("❌ Invalid stock count. Please enter a positive number:")
    
    async def show_users_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show list of all users"""
        users = self.db.get_all_users()
        
        if not users:
            text = "❌ No users found."
            keyboard = self.keyboards.back_button()
        else:
            text = "👤 Select a user to manage:"
            keyboard = self.keyboards.users_list_menu(users)
        
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=keyboard
        )
    
    async def show_user_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str):
        """Show user management options"""
        user = self.db.get_user(int(user_id))
        
        if not user:
            text = "❌ User not found."
            keyboard = self.keyboards.back_button()
        else:
            username = format_user_mention(user['username'])
            text = f"💰 Manage Coins for {username} – {format_price(user['coins'])}"
            keyboard = self.keyboards.user_management_menu(user_id)
        
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=keyboard
        )
    
    async def start_coin_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE, action: str, user_id: str):
        """Start coin add/remove flow"""
        admin_id = update.effective_user.id
        self.admin_states[admin_id] = {
            'action': f'coin_{action}',
            'target_user_id': user_id
        }
        
        action_text = "add" if action == "add" else "remove"
        await update.callback_query.edit_message_text(
            text=f"💰 Enter amount to {action_text}:",
            reply_markup=self.keyboards.back_button()
        )
    
    async def handle_coin_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle coin add/remove"""
        admin_id = update.effective_user.id
        text = update.message.text.strip()
        
        if admin_id not in self.admin_states:
            return
        
        state = self.admin_states[admin_id]
        target_user_id = int(state['target_user_id'])
        amount = validate_positive_integer(text)
        
        if not amount:
            await update.message.reply_text("❌ Invalid amount. Please enter a positive number:")
            return
        
        user = self.db.get_user(target_user_id)
        if not user:
            await update.message.reply_text("❌ User not found.")
            del self.admin_states[admin_id]
            return
        
        if state['action'] == 'coin_add':
            self.db.update_user_coins(target_user_id, amount)
            action_text = "added"
        else:  # coin_remove
            self.db.update_user_coins(target_user_id, -amount)
            action_text = "removed"
        
        updated_user = self.db.get_user(target_user_id)
        username = format_user_mention(updated_user['username'])
        
        confirmation_text = f"""✅ Coins {action_text}!

{username} now has {format_price(updated_user['coins'])}"""
        
        await update.message.reply_text(
            confirmation_text,
            reply_markup=self.keyboards.back_button()
        )
        
        del self.admin_states[admin_id]
    
    async def show_pending_orders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show pending orders"""
        orders = self.db.get_pending_orders()
        
        if not orders:
            text = "📦 No pending orders."
            keyboard = self.keyboards.back_button()
        else:
            text = "📦 Pending Orders:\n\nSelect an order to manage:"
            keyboard = self.keyboards.orders_menu(orders)
        
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=keyboard
        )
    
    async def show_order_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str):
        """Show order details"""
        orders = self.db.get_pending_orders()
        order = next((o for o in orders if o['order_id'] == order_id), None)
        
        if not order:
            text = "❌ Order not found or already processed."
            keyboard = self.keyboards.back_button()
        else:
            item = self.db.get_item(order['item_id'])
            user = self.db.get_user(order['user_id'])
            
            item_name = item['name'] if item else 'Unknown Item'
            item_price = item['price'] if item else 0
            username = format_user_mention(user['username']) if user else 'Unknown User'
            
            text = f"""📦 Order Details

🆔 Order ID: {order_id}
👤 Customer: {username}
🎮 Item: {item_name}
💰 Price: {format_price(item_price)}
📅 Date: {order['created_at'][:16]}"""
            
            keyboard = self.keyboards.order_action_menu(order_id)
        
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=keyboard
        )
    
    async def process_order_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE, action: str, order_id: str):
        """Process order confirmation or rejection"""
        orders = self.db.get_pending_orders()
        order = next((o for o in orders if o['order_id'] == order_id), None)
        
        if not order:
            text = "❌ Order not found or already processed."
        else:
            item = self.db.get_item(order['item_id'])
            user = self.db.get_user(order['user_id'])
            
            if action == "confirm":
                if item and item['stock'] > 0:
                    # Deduct coins
                    self.db.update_user_coins(order['user_id'], -item['price'])
                    # Reduce stock
                    self.db.update_item_stock(order['item_id'], item['stock'] - 1)
                    # Update order status
                    self.db.update_order_status(order_id, 'confirmed')
                    
                    text = f"✅ Order {order_id} confirmed!\n\nUser coins deducted and item stock updated."
                    
                    # Notify user (you might want to implement this)
                    try:
                        await context.bot.send_message(
                            chat_id=order['user_id'],
                            text=f"✅ Your order {order_id} has been confirmed!\n🎮 {item['name']} is ready for delivery."
                        )
                    except:
                        pass  # User might have blocked the bot
                else:
                    text = "❌ Cannot confirm order - item out of stock."
            
            else:  # reject
                self.db.update_order_status(order_id, 'rejected')
                text = f"❌ Order {order_id} rejected."
                
                # Notify user
                try:
                    await context.bot.send_message(
                        chat_id=order['user_id'],
                        text=f"❌ Your order {order_id} has been rejected.\nPlease contact support if you have questions."
                    )
                except:
                    pass
        
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=self.keyboards.back_button()
        )
    
    async def start_add_coupon_flow(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start add coupon flow"""
        admin_id = update.effective_user.id
        self.admin_states[admin_id] = {
            'action': 'add_coupon_code',
            'coupon_data': {}
        }
        
        await update.message.reply_text(
            text="🏷️ Adding New Coupon\n\nEnter coupon code (e.g., NEWYEAR):",
            reply_markup=self.keyboards.back_button()
        )
    
    async def handle_add_coupon_steps(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle add coupon steps"""
        admin_id = update.effective_user.id
        text = update.message.text.strip()
        
        if admin_id not in self.admin_states:
            return
        
        state = self.admin_states[admin_id]
        
        if state['action'] == 'add_coupon_code':
            state['coupon_data']['code'] = text.upper()
            state['action'] = 'add_coupon_discount'
            await update.message.reply_text("Enter discount amount (MMK):")
            
        elif state['action'] == 'add_coupon_discount':
            discount = validate_positive_integer(text)
            if discount:
                # Save coupon
                code = state['coupon_data']['code']
                self.db.add_coupon(code, discount)
                
                confirmation_text = f"""🏷️ Coupon "{code}" saved – {format_price(discount)} discount

Users can now use this coupon when purchasing items."""
                
                await update.message.reply_text(
                    confirmation_text,
                    reply_markup=self.keyboards.back_button()
                )
                
                del self.admin_states[admin_id]
            else:
                await update.message.reply_text("❌ Invalid discount amount. Please enter a positive number:")
    
    async def show_items_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show items management list"""
        items = self.db.get_all_items()
        
        if not items:
            text = "❌ No items found. Add some items first!"
            keyboard = self.keyboards.back_button()
        else:
            text = "📝 Select an item to manage:"
            keyboard = self.keyboards.items_management_menu(items)
        
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=keyboard
        )
    
    async def show_item_management_actions(self, update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: str):
        """Show item management actions"""
        item = self.db.get_item(item_id)
        
        if not item:
            text = "❌ Item not found."
            keyboard = self.keyboards.back_button()
        else:
            text = f"""📝 Managing Item

🎮 Name: {item['name']}
📁 Category: {item['category']}
💰 Price: {format_price(item['price'])}
📦 Stock: {item['stock']}

Choose an action:"""
            keyboard = self.keyboards.item_management_actions(item_id)
        
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=keyboard
        )
    
    async def start_edit_item_flow(self, update: Update, context: ContextTypes.DEFAULT_TYPE, action: str, item_id: str):
        """Start edit item flow (stock or price)"""
        admin_id = update.effective_user.id
        item = self.db.get_item(item_id)
        
        if not item:
            await update.callback_query.edit_message_text(
                text="❌ Item not found.",
                reply_markup=self.keyboards.back_button()
            )
            return
        
        self.admin_states[admin_id] = {
            'action': f'edit_{action}',
            'item_id': item_id
        }
        
        current_value = item['stock'] if action == 'stock' else item['price']
        field_name = "stock count" if action == 'stock' else "price (MMK)"
        
        await update.callback_query.edit_message_text(
            text=f"✏️ Current {field_name}: {current_value}\n\nEnter new {field_name}:",
            reply_markup=self.keyboards.back_button()
        )
    
    async def handle_edit_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle edit item steps"""
        admin_id = update.effective_user.id
        text = update.message.text.strip()
        
        if admin_id not in self.admin_states:
            return
        
        state = self.admin_states[admin_id]
        item_id = state['item_id']
        value = validate_positive_integer(text)
        
        if not value:
            field = "stock count" if state['action'] == 'edit_stock' else "price"
            await update.message.reply_text(f"❌ Invalid {field}. Please enter a positive number:")
            return
        
        item = self.db.get_item(item_id)
        if not item:
            await update.message.reply_text("❌ Item not found.")
            del self.admin_states[admin_id]
            return
        
        if state['action'] == 'edit_stock':
            self.db.update_item_stock(item_id, value)
            field_name = "stock"
        else:  # edit_price
            self.db.update_item_price(item_id, value)
            field_name = "price"
        
        confirmation_text = f"""✅ Item {field_name} updated!

🎮 {item['name']}
New {field_name}: {value if field_name == 'stock' else format_price(value)}"""
        
        await update.message.reply_text(
            confirmation_text,
            reply_markup=self.keyboards.back_button()
        )
        
        del self.admin_states[admin_id]
    
    async def confirm_delete_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: str):
        """Show delete confirmation"""
        item = self.db.get_item(item_id)
        
        if not item:
            text = "❌ Item not found."
            keyboard = self.keyboards.back_button()
        else:
            text = f"""⚠️ Delete Confirmation

Are you sure you want to delete this item?

🎮 Name: {item['name']}
📁 Category: {item['category']}
💰 Price: {format_price(item['price'])}
📦 Stock: {item['stock']}

This action cannot be undone!"""
            keyboard = self.keyboards.confirm_delete_menu(item_id)
        
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=keyboard
        )
    
    async def delete_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: str):
        """Delete item"""
        item = self.db.get_item(item_id)
        
        if not item:
            text = "❌ Item not found."
        else:
            success = self.db.delete_item(item_id)
            if success:
                text = f"✅ Item '{item['name']}' has been deleted successfully!"
            else:
                text = "❌ Failed to delete item."
        
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=self.keyboards.back_button()
        )
    
    async def show_coupons_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show coupons management list"""
        coupons = self.db.get_all_coupons()
        
        if not coupons:
            text = "❌ No coupons found. Add some coupons first!"
            keyboard = self.keyboards.back_button()
        else:
            text = "🎫 Select a coupon to manage:"
            keyboard = self.keyboards.coupons_management_menu(coupons)
        
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=keyboard
        )
    
    async def show_coupon_management_actions(self, update: Update, context: ContextTypes.DEFAULT_TYPE, code: str):
        """Show coupon management actions"""
        coupon = self.db.get_coupon(code)
        
        if not coupon:
            text = "❌ Coupon not found."
            keyboard = self.keyboards.back_button()
        else:
            text = f"""🎫 Managing Coupon

🏷️ Code: {code}
💰 Discount: {format_price(coupon['discount'])}
📅 Created: {coupon.get('created_at', 'Unknown')[:10]}

Choose an action:"""
            keyboard = self.keyboards.coupon_management_actions(code)
        
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=keyboard
        )
    
    async def start_edit_coupon_flow(self, update: Update, context: ContextTypes.DEFAULT_TYPE, code: str):
        """Start edit coupon discount flow"""
        admin_id = update.effective_user.id
        coupon = self.db.get_coupon(code)
        
        if not coupon:
            await update.callback_query.edit_message_text(
                text="❌ Coupon not found.",
                reply_markup=self.keyboards.back_button()
            )
            return
        
        self.admin_states[admin_id] = {
            'action': 'edit_coupon_discount',
            'coupon_code': code
        }
        
        current_discount = coupon['discount']
        
        await update.callback_query.edit_message_text(
            text=f"✏️ Current discount: {format_price(current_discount)}\n\nEnter new discount amount (MMK):",
            reply_markup=self.keyboards.back_button()
        )
    
    async def handle_edit_coupon(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle edit coupon discount"""
        admin_id = update.effective_user.id
        text = update.message.text.strip()
        
        if admin_id not in self.admin_states:
            return
        
        state = self.admin_states[admin_id]
        code = state['coupon_code']
        discount = validate_positive_integer(text)
        
        if not discount:
            await update.message.reply_text("❌ Invalid discount amount. Please enter a positive number:")
            return
        
        coupon = self.db.get_coupon(code)
        if not coupon:
            await update.message.reply_text("❌ Coupon not found.")
            del self.admin_states[admin_id]
            return
        
        self.db.update_coupon_discount(code, discount)
        
        confirmation_text = f"""✅ Coupon discount updated!

🏷️ Code: {code}
New discount: {format_price(discount)}"""
        
        await update.message.reply_text(
            confirmation_text,
            reply_markup=self.keyboards.back_button()
        )
        
        del self.admin_states[admin_id]
    
    async def confirm_delete_coupon(self, update: Update, context: ContextTypes.DEFAULT_TYPE, code: str):
        """Show coupon delete confirmation"""
        coupon = self.db.get_coupon(code)
        
        if not coupon:
            text = "❌ Coupon not found."
            keyboard = self.keyboards.back_button()
        else:
            text = f"""⚠️ Delete Coupon Confirmation

Are you sure you want to delete this coupon?

🏷️ Code: {code}
💰 Discount: {format_price(coupon['discount'])}

This action cannot be undone!"""
            keyboard = self.keyboards.confirm_delete_coupon_menu(code)
        
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=keyboard
        )
    
    async def delete_coupon(self, update: Update, context: ContextTypes.DEFAULT_TYPE, code: str):
        """Delete coupon"""
        coupon = self.db.get_coupon(code)
        
        if not coupon:
            text = "❌ Coupon not found."
        else:
            success = self.db.delete_coupon(code)
            if success:
                text = f"✅ Coupon '{code}' has been deleted successfully!"
            else:
                text = "❌ Failed to delete coupon."
        
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=self.keyboards.back_button()
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle admin callback queries"""
        query = update.callback_query
        data = query.data
        
        if data == "admin_add_item":
            await self.start_add_item_flow(update, context)
        elif data == "admin_manage_items":
            await self.show_items_management(update, context)
        elif data == "admin_view_users":
            await self.show_users_list(update, context)
        elif data == "admin_manage_coins":
            await self.show_users_list(update, context)
        elif data == "admin_view_orders":
            await self.show_pending_orders(update, context)
        elif data == "admin_add_coupon":
            await self.start_add_coupon_flow(update, context)
        elif data == "admin_manage_coupons":
            await self.show_coupons_management(update, context)
        elif data.startswith("admin_user_"):
            user_id = data.replace("admin_user_", "")
            await self.show_user_management(update, context, user_id)
        elif data.startswith("admin_add_coins_"):
            user_id = data.replace("admin_add_coins_", "")
            await self.start_coin_management(update, context, "add", user_id)
        elif data.startswith("admin_remove_coins_"):
            user_id = data.replace("admin_remove_coins_", "")
            await self.start_coin_management(update, context, "remove", user_id)
        elif data.startswith("admin_order_"):
            order_id = data.replace("admin_order_", "")
            await self.show_order_detail(update, context, order_id)
        elif data.startswith("admin_confirm_"):
            order_id = data.replace("admin_confirm_", "")
            await self.process_order_action(update, context, "confirm", order_id)
        elif data.startswith("admin_reject_"):
            order_id = data.replace("admin_reject_", "")
            await self.process_order_action(update, context, "reject", order_id)
        elif data.startswith("admin_item_"):
            item_id = data.replace("admin_item_", "")
            await self.show_item_management_actions(update, context, item_id)
        elif data.startswith("admin_edit_stock_"):
            item_id = data.replace("admin_edit_stock_", "")
            await self.start_edit_item_flow(update, context, "stock", item_id)
        elif data.startswith("admin_edit_price_"):
            item_id = data.replace("admin_edit_price_", "")
            await self.start_edit_item_flow(update, context, "price", item_id)
        elif data.startswith("admin_delete_"):
            item_id = data.replace("admin_delete_", "")
            await self.confirm_delete_item(update, context, item_id)
        elif data.startswith("admin_confirm_delete_"):
            item_id = data.replace("admin_confirm_delete_", "")
            await self.delete_item(update, context, item_id)
        elif data.startswith("admin_coupon_"):
            code = data.replace("admin_coupon_", "")
            await self.show_coupon_management_actions(update, context, code)
        elif data.startswith("admin_edit_coupon_"):
            code = data.replace("admin_edit_coupon_", "")
            await self.start_edit_coupon_flow(update, context, code)
        elif data.startswith("admin_delete_coupon_"):
            code = data.replace("admin_delete_coupon_", "")
            await self.confirm_delete_coupon(update, context, code)
        elif data.startswith("admin_confirm_delete_coupon_"):
            code = data.replace("admin_confirm_delete_coupon_", "")
            await self.delete_coupon(update, context, code)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages from admin"""
        admin_id = update.effective_user.id
        
        if admin_id in self.admin_states:
            state = self.admin_states[admin_id]
            
            if state['action'].startswith('add_item_'):
                await self.handle_add_item_steps(update, context)
            elif state['action'].startswith('coin_'):
                await self.handle_coin_management(update, context)
            elif state['action'].startswith('add_coupon_'):
                await self.handle_add_coupon_steps(update, context)
            elif state['action'].startswith('edit_') and 'item_id' in state:
                await self.handle_edit_item(update, context)
            elif state['action'] == 'edit_coupon_discount':
                await self.handle_edit_coupon(update, context)
        else:
            # Handle main menu button presses
            text = update.message.text
            if text == "➕ Add Item":
                await self.start_add_item_flow(update, context)
            elif text == "📝 Manage Items":
                await self.show_items_management(update, context)
            elif text == "👤 View Users":
                await self.show_users_list(update, context)
            elif text == "💰 Manage Coins":
                await self.show_users_list(update, context)
            elif text == "📦 View Orders":
                await self.show_pending_orders(update, context)
            elif text == "🏷️ Add Coupon":
                await self.start_add_coupon_flow(update, context)
            elif text == "🎫 Manage Coupons":
                await self.show_coupons_management(update, context)
            else:
                await update.message.reply_text("Please use the menu buttons or type /start")
