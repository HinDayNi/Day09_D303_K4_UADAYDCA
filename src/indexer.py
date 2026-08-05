import os
import pandas as pd

class OlistIndexer:
    def __init__(self, data_dir="data"):
        self.orders = pd.read_csv(os.path.join(data_dir, "olist_orders_dataset.csv")).set_index("order_id").to_dict("index")
        self.customers = pd.read_csv(os.path.join(data_dir, "olist_customers_dataset.csv")).set_index("customer_id").to_dict("index")
        self.products = pd.read_csv(os.path.join(data_dir, "olist_products_dataset.csv")).set_index("product_id").to_dict("index")
        self.items_df = pd.read_csv(os.path.join(data_dir, "olist_order_items_dataset.csv"))
        self.payments_df = pd.read_csv(os.path.join(data_dir, "olist_order_payments_dataset.csv"))
        self.cust_unique_df = pd.read_csv(os.path.join(data_dir, "olist_customers_dataset.csv"))

    def get_order_context(self, order_id):
        order_info = self.orders.get(order_id, {})
        items = self.items_df[self.items_df["order_id"] == order_id].to_dict("records")
        payments = self.payments_df[self.payments_df["order_id"] == order_id].to_dict("records")
        
        customer_id = order_info.get("customer_id")
        customer_info = self.customers.get(customer_id, {})
        customer_unique_id = customer_info.get("customer_unique_id")

        related_orders = []
        if customer_unique_id:
            related_cust_ids = self.cust_unique_df[self.cust_unique_df["customer_unique_id"] == customer_unique_id]["customer_id"].tolist()
            for o_id, o_data in self.orders.items():
                if o_data.get("customer_id") in related_cust_ids and o_id != order_id:
                    related_orders.append(o_id)

        return {
            "order_id": order_id,
            "order_info": order_info,
            "items": items,
            "payments": payments,
            "customer_unique_id": customer_unique_id,
            "related_order_ids": related_orders
        }