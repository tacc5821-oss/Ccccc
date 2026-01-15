from telegram import Update
from telegram.ext import ContextTypes
from bot.keyboards import Keyboards
from bot.database import Database
from bot.utils import format_price, format_order_status

class UserHandlers:
    def __init__(self, database: Database):
        self.db = database
        self.keyboards = Keyboards()
        self.user_states = {}  # Track user states for multi-step flows
    
    async def show_user_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main user menu"""
        text = "🎮 Welcome to Gaming Items Store!\n\nSelect an option:"
        
        if update.callback_query:
            await update.callback_query.message.reply_text(
                text=text,
                reply_markup=self.keyboards.user_main_menu()
            )
        else:
            await update.message.reply_text(
                text=text,
                reply_markup=self.keyboards.user_main_menu()
            )
    
    async def show_categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show available categories"""
        categories = self.db.get_all_categories()
        
        if not categories:
            text = "❌ No items available yet. Please check back later!"
            keyboard = self.keyboards.back_button()
        else:
            text = "🛍️ Select a category:"
            keyboard = self.keyboards.categories_menu(categories)
        
        await update.message.reply_text(
            text=text,
            reply_markup=keyboard
        )
    
    async def show_category_items(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category: str):
        """Show items in selected category"""
        items = self.db.get_items_by_category(category)
        
        if not items:
            text = f"❌ No items found in {category} category."
            keyboard = self.keyboards.back_button()
        else:
            text = f"🎮 {category} Items:"
            keyboard = self.keyboards.items_menu(items, category)
        
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=keyboard
        )
    
    async def show_item_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: str):
        """Show item details"""
        item = self.db.get_item(item_id)
        
        if not item:
            text = "❌ Item not found."
            keyboard = self.keyboards.back_button()
        else:
            in_stock = item['stock'] > 0
            stock_text = f"📦 Stock: {item['stock']}" if in_stock else "❌ Out of Stock"
            
            text = f"""🎮 {item['name']}
            
📁 Category: {item['category']}
💰 Price: {format_price(item['price'])}
{stock_text}"""
            
            keyboard = self.keyboards.item_detail_menu(item_id, in_stock)
        
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=keyboard
        )
    
    async def show_purchase_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: str):
        """Show purchase confirmation"""
        item = self.db.get_item(item_id)
        user = self.db.get_user(update.effective_user.id)
        
        if not item or not user:
            text = "❌ Error processing request."
            keyboard = self.keyboards.back_button()
        elif item['stock'] <= 0:
            text = "❌ This item is out of stock."
            keyboard = self.keyboards.back_button()
        else:
            user_coins = user['coins']
            can_afford = user_coins >= item['price']
            
            text = f"""💰 Purchase Confirmation
            
🎮 Item: {item['name']}
💰 Price: {format_price(item['price'])}
💳 Your Balance: {format_price(user_coins)}
            
{'✅ You can afford this item!' if can_afford else '❌ Insufficient funds!'}"""
            
            if can_afford:
                keyboard = self.keyboards.purchase_confirmation_menu(item_id)
            else:
                keyboard = self.keyboards.back_button()
        
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=keyboard
        )
    
    async def process_purchase(self, update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: str, coupon_discount: int = 0):
        """Process the actual purchase"""
        user_id = update.effective_user.id
        item = self.db.get_item(item_id)
        user = self.db.get_user(user_id)
        
        if not item or not user:
            text = "❌ Error processing purchase."
        elif item['stock'] <= 0:
            text = "❌ Item is out of stock."
        else:
            final_price = max(0, item['price'] - coupon_discount)
            
            if user['coins'] >= final_price:
                # Create order
                order_id = self.db.create_order(user_id, item_id)
                
                text = f"""✅ Order Created!
                
📦 Order ID: {order_id}
🎮 Item: {item['name']}
💰 Price: {format_price(final_price)}
{'🏷️ Coupon Discount: ' + format_price(coupon_discount) if coupon_discount > 0 else ''}

⏳ Your order is pending admin confirmation.
You will be notified once it's processed."""
            else:
                text = f"❌ Insufficient funds!\nRequired: {format_price(final_price)}\nYour balance: {format_price(user['coins'])}"
        
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=self.keyboards.back_button()
        )
    
    async def show_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user balance"""
        user = self.db.get_user(update.effective_user.id)
        
        if user:
            text = f"💰 Your Balance: {format_price(user['coins'])}"
        else:
            text = "❌ User not found."
        
        await update.message.reply_text(
            text=text,
            reply_markup=self.keyboards.back_button()
        )
    
    async def show_user_orders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user's order history"""
        user_id = update.effective_user.id
        orders = self.db.get_user_orders(user_id)
        
        if not orders:
            text = "📦 You have no orders yet."
        else:
            text = "📦 Your Orders:\n\n"
            for order in orders[-10:]:  # Show last 10 orders
                item = self.db.get_item(order['item_id'])
                item_name = item['name'] if item else 'Unknown Item'
                status = format_order_status(order['status'])
                text += f"🎮 {item_name}\n{status}\n📅 {order['created_at'][:10]}\n\n"
        
        await update.message.reply_text(
            text=text,
            reply_markup=self.keyboards.back_button()
        )
    
    async def handle_coupon_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle coupon code input"""
        user_id = update.effective_user.id
        
        if user_id in self.user_states and self.user_states[user_id]['action'] == 'coupon_input':
            coupon_code = update.message.text.strip().upper()
            item_id = self.user_states[user_id]['item_id']
            
            coupon = self.db.get_coupon(coupon_code)
            
            if coupon:
                # Process purchase with discount
                await update.message.reply_text(f"🏷️ Coupon '{coupon_code}' applied! Discount: {format_price(coupon['discount'])}")
                
                # Create a fake callback query to reuse purchase logic
                class FakeQuery:
                    def __init__(self, user_id):
                        self.from_user = type('obj', (object,), {'id': user_id})
                        
                    async def edit_message_text(self, text, reply_markup):
                        await update.message.reply_text(text, reply_markup=reply_markup)
                
                fake_update = type('obj', (object,), {
                    'effective_user': update.effective_user,
                    'callback_query': FakeQuery(user_id)
                })()
                
                await self.process_purchase(fake_update, context, item_id, coupon['discount'])
            else:
                await update.message.reply_text("❌ Invalid coupon code. Please try again or type /start to return to menu.")
            
            # Clear state
            del self.user_states[user_id]
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle user callback queries"""
        query = update.callback_query
        data = query.data
        
        if data == "user_browse":
            await self.show_categories(update, context)
        elif data == "user_balance":
            await self.show_balance(update, context)
        elif data == "user_orders":
            await self.show_user_orders(update, context)
        elif data.startswith("category_"):
            category = data.replace("category_", "")
            await self.show_category_items(update, context, category)
        elif data.startswith("item_"):
            item_id = data.replace("item_", "")
            await self.show_item_detail(update, context, item_id)
        elif data.startswith("buy_"):
            item_id = data.replace("buy_", "")
            await self.show_purchase_confirmation(update, context, item_id)
        elif data.startswith("confirm_buy_"):
            item_id = data.replace("confirm_buy_", "")
            await self.process_purchase(update, context, item_id)
        elif data.startswith("coupon_"):
            item_id = data.replace("coupon_", "")
            self.user_states[update.effective_user.id] = {
                'action': 'coupon_input',
                'item_id': item_id
            }
            await query.edit_message_text(
                text="🏷️ Enter coupon code:",
                reply_markup=self.keyboards.back_button()
            )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages from users"""
        user_id = update.effective_user.id
        
        if user_id in self.user_states:
            if self.user_states[user_id]['action'] == 'coupon_input':
                await self.handle_coupon_input(update, context)
            else:
                await update.message.reply_text("Please use the menu buttons or type /start")
        else:
            # Handle main menu button presses
            text = update.message.text
            if text == "🛍️ Browse Items":
                await self.show_categories(update, context)
            elif text == "💰 My Balance":
                await self.show_balance(update, context)
            elif text == "📦 My Orders":
                await self.show_user_orders(update, context)
            else:
                await update.message.reply_text("Please use the menu buttons or type /start")
