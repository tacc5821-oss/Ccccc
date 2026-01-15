import json
import os
from typing import Dict, List, Optional
from datetime import datetime

class Database:
    def __init__(self):
        self.data_dir = 'data'
        self.users_file = os.path.join(self.data_dir, 'users.json')
        self.items_file = os.path.join(self.data_dir, 'items.json')
        self.orders_file = os.path.join(self.data_dir, 'orders.json')
        self.coupons_file = os.path.join(self.data_dir, 'coupons.json')
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Initialize empty files if they don't exist
        self._init_file(self.users_file, {})
        self._init_file(self.items_file, {})
        self._init_file(self.orders_file, [])
        self._init_file(self.coupons_file, {})
    
    def _init_file(self, filepath: str, default_data):
        """Initialize file with default data if it doesn't exist"""
        if not os.path.exists(filepath):
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, ensure_ascii=False, indent=2)
    
    def _load_json(self, filepath: str):
        """Load JSON data from file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {} if 'users' in filepath or 'items' in filepath or 'coupons' in filepath else []
    
    def _save_json(self, filepath: str, data):
        """Save data to JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    # User management
    def register_user(self, user_id: int, username: str):
        """Register new user or update existing"""
        users = self._load_json(self.users_file)
        if str(user_id) not in users:
            users[str(user_id)] = {
                'username': username,
                'coins': 0,
                'registered_at': datetime.now().isoformat()
            }
        else:
            users[str(user_id)]['username'] = username
        self._save_json(self.users_file, users)
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user data"""
        users = self._load_json(self.users_file)
        return users.get(str(user_id))
    
    def get_all_users(self) -> Dict:
        """Get all users"""
        return self._load_json(self.users_file)
    
    def update_user_coins(self, user_id: int, amount: int):
        """Update user coins (can be positive or negative)"""
        users = self._load_json(self.users_file)
        if str(user_id) in users:
            users[str(user_id)]['coins'] = max(0, users[str(user_id)]['coins'] + amount)
            self._save_json(self.users_file, users)
    
    def set_user_coins(self, user_id: int, amount: int):
        """Set user coins to specific amount"""
        users = self._load_json(self.users_file)
        if str(user_id) in users:
            users[str(user_id)]['coins'] = max(0, amount)
            self._save_json(self.users_file, users)
    
    # Item management
    def add_item(self, category: str, name: str, price: int, stock: int) -> str:
        """Add new item and return item ID"""
        items = self._load_json(self.items_file)
        item_id = f"{category}_{len([i for i in items.values() if i['category'] == category]) + 1}"
        
        items[item_id] = {
            'category': category,
            'name': name,
            'price': price,
            'stock': stock,
            'created_at': datetime.now().isoformat()
        }
        self._save_json(self.items_file, items)
        return item_id
    
    def get_items_by_category(self, category: str) -> Dict:
        """Get all items in a category"""
        items = self._load_json(self.items_file)
        return {k: v for k, v in items.items() if v['category'] == category}
    
    def get_all_categories(self) -> List[str]:
        """Get all unique categories"""
        items = self._load_json(self.items_file)
        return list(set(item['category'] for item in items.values()))
    
    def get_item(self, item_id: str) -> Optional[Dict]:
        """Get specific item"""
        items = self._load_json(self.items_file)
        return items.get(item_id)
    
    def update_item_stock(self, item_id: str, new_stock: int):
        """Update item stock"""
        items = self._load_json(self.items_file)
        if item_id in items:
            items[item_id]['stock'] = max(0, new_stock)
            self._save_json(self.items_file, items)
    
    def update_item_price(self, item_id: str, new_price: int):
        """Update item price"""
        items = self._load_json(self.items_file)
        if item_id in items:
            items[item_id]['price'] = max(0, new_price)
            self._save_json(self.items_file, items)
    
    def delete_item(self, item_id: str):
        """Delete an item"""
        items = self._load_json(self.items_file)
        if item_id in items:
            del items[item_id]
            self._save_json(self.items_file, items)
            return True
        return False
    
    def get_all_items(self) -> Dict:
        """Get all items"""
        return self._load_json(self.items_file)
    
    # Order management
    def create_order(self, user_id: int, item_id: str, quantity: int = 1) -> str:
        """Create new order"""
        orders = self._load_json(self.orders_file)
        order_id = f"order_{len(orders) + 1}"
        
        order = {
            'order_id': order_id,
            'user_id': user_id,
            'item_id': item_id,
            'quantity': quantity,
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }
        orders.append(order)
        self._save_json(self.orders_file, orders)
        return order_id
    
    def get_pending_orders(self) -> List[Dict]:
        """Get all pending orders"""
        orders = self._load_json(self.orders_file)
        return [order for order in orders if order['status'] == 'pending']
    
    def get_user_orders(self, user_id: int) -> List[Dict]:
        """Get all orders for a user"""
        orders = self._load_json(self.orders_file)
        return [order for order in orders if order['user_id'] == user_id]
    
    def update_order_status(self, order_id: str, status: str):
        """Update order status"""
        orders = self._load_json(self.orders_file)
        for order in orders:
            if order['order_id'] == order_id:
                order['status'] = status
                order['updated_at'] = datetime.now().isoformat()
                break
        self._save_json(self.orders_file, orders)
    
    # Coupon management
    def add_coupon(self, code: str, discount: int):
        """Add new coupon"""
        coupons = self._load_json(self.coupons_file)
        coupons[code.upper()] = {
            'discount': discount,
            'created_at': datetime.now().isoformat()
        }
        self._save_json(self.coupons_file, coupons)
    
    def get_coupon(self, code: str) -> Optional[Dict]:
        """Get coupon by code"""
        coupons = self._load_json(self.coupons_file)
        return coupons.get(code.upper())
    
    def get_all_coupons(self) -> Dict:
        """Get all coupons"""
        return self._load_json(self.coupons_file)
    
    def update_coupon_discount(self, code: str, new_discount: int):
        """Update coupon discount amount"""
        coupons = self._load_json(self.coupons_file)
        if code.upper() in coupons:
            coupons[code.upper()]['discount'] = max(0, new_discount)
            self._save_json(self.coupons_file, coupons)
    
    def delete_coupon(self, code: str):
        """Delete a coupon"""
        coupons = self._load_json(self.coupons_file)
        if code.upper() in coupons:
            del coupons[code.upper()]
            self._save_json(self.coupons_file, coupons)
            return True
        return False
