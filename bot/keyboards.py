from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from typing import List, Dict

class Keyboards:
    @staticmethod
    def admin_main_menu():
        """Main admin menu keyboard"""
        keyboard = [
            [KeyboardButton("➕ Add Item"), KeyboardButton("📝 Manage Items")],
            [KeyboardButton("👤 View Users"), KeyboardButton("💰 Manage Coins")],
            [KeyboardButton("📦 View Orders")],
            [KeyboardButton("🏷️ Add Coupon"), KeyboardButton("🎫 Manage Coupons")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    @staticmethod
    def user_main_menu():
        """Main user menu keyboard"""
        keyboard = [
            [KeyboardButton("🛍️ Browse Items")],
            [KeyboardButton("💰 My Balance"), KeyboardButton("📦 My Orders")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    @staticmethod
    def categories_menu(categories: List[str]):
        """Categories selection keyboard"""
        keyboard = []
        for category in categories:
            keyboard.append([InlineKeyboardButton(f"🎮 {category}", callback_data=f"category_{category}")])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_main")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def items_menu(items: Dict, category: str):
        """Items in category keyboard"""
        keyboard = []
        for item_id, item in items.items():
            stock_text = f"({item['stock']} left)" if item['stock'] > 0 else "(Out of stock)"
            button_text = f"{item['name']} - {item['price']:,} MMK {stock_text}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"item_{item_id}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Categories", callback_data="back_to_categories")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def item_detail_menu(item_id: str, in_stock: bool):
        """Item detail keyboard"""
        keyboard = []
        if in_stock:
            keyboard.append([InlineKeyboardButton("💰 Buy Now", callback_data=f"buy_{item_id}")])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_categories")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def users_list_menu(users: Dict):
        """Users list keyboard for admin"""
        keyboard = []
        for user_id, user in users.items():
            username = user.get('username', 'Unknown')
            coins = user.get('coins', 0)
            button_text = f"@{username} – {coins:,} MMK"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"admin_user_{user_id}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_admin")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def user_management_menu(user_id: str):
        """User management keyboard for admin"""
        keyboard = [
            [InlineKeyboardButton("➕ Add Coins", callback_data=f"admin_add_coins_{user_id}")],
            [InlineKeyboardButton("➖ Remove Coins", callback_data=f"admin_remove_coins_{user_id}")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_view_users")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def orders_menu(orders: List[Dict]):
        """Orders management keyboard for admin"""
        keyboard = []
        for order in orders[:10]:  # Show max 10 orders
            order_id = order['order_id']
            user_id = order['user_id']
            keyboard.append([InlineKeyboardButton(f"Order {order_id}", callback_data=f"admin_order_{order_id}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_admin")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def order_action_menu(order_id: str):
        """Order action keyboard for admin"""
        keyboard = [
            [InlineKeyboardButton("✅ Confirm", callback_data=f"admin_confirm_{order_id}")],
            [InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_{order_id}")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_view_orders")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def purchase_confirmation_menu(item_id: str):
        """Purchase confirmation keyboard"""
        keyboard = [
            [InlineKeyboardButton("✅ Confirm Purchase", callback_data=f"confirm_buy_{item_id}")],
            [InlineKeyboardButton("🏷️ Use Coupon", callback_data=f"coupon_{item_id}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="back_to_categories")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def back_button():
        """Simple back button"""
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def items_management_menu(items: Dict):
        """Items management keyboard for admin"""
        keyboard = []
        for item_id, item in items.items():
            stock_text = f"({item['stock']} left)" if item['stock'] > 0 else "(Out of stock)"
            button_text = f"{item['name']} - {item['category']} {stock_text}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"admin_item_{item_id}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_admin")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def item_management_actions(item_id: str):
        """Item management actions keyboard"""
        keyboard = [
            [InlineKeyboardButton("✏️ Edit Stock", callback_data=f"admin_edit_stock_{item_id}")],
            [InlineKeyboardButton("💰 Edit Price", callback_data=f"admin_edit_price_{item_id}")],
            [InlineKeyboardButton("❌ Delete Item", callback_data=f"admin_delete_{item_id}")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_manage_items")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def confirm_delete_menu(item_id: str):
        """Confirm delete item keyboard"""
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"admin_confirm_delete_{item_id}")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"admin_item_{item_id}")],
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def coupons_management_menu(coupons: Dict):
        """Coupons management keyboard for admin"""
        keyboard = []
        for code, coupon in coupons.items():
            discount = coupon.get('discount', 0)
            button_text = f"{code} - {discount:,} MMK discount"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"admin_coupon_{code}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_admin")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def coupon_management_actions(code: str):
        """Coupon management actions keyboard"""
        keyboard = [
            [InlineKeyboardButton("✏️ Edit Discount", callback_data=f"admin_edit_coupon_{code}")],
            [InlineKeyboardButton("❌ Delete Coupon", callback_data=f"admin_delete_coupon_{code}")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_manage_coupons")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def confirm_delete_coupon_menu(code: str):
        """Confirm delete coupon keyboard"""
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"admin_confirm_delete_coupon_{code}")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"admin_coupon_{code}")],
        ]
        return InlineKeyboardMarkup(keyboard)
