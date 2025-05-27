import os
import sqlite3
import pandas as pd
from agentic_processor import AgenticQueryProcessor

def create_test_database():
    """Create a test database with multiple tables for join testing."""
    # Remove existing test database if it exists
    if os.path.exists("test_joins.db"):
        os.remove("test_joins.db")
    
    # Create a new database
    conn = sqlite3.connect("test_joins.db")
    
    # Create customers table
    customers_df = pd.DataFrame({
        'customer_id': [1, 2, 3, 4, 5],
        'name': ['John Smith', 'Jane Doe', 'Bob Johnson', 'Alice Brown', 'Charlie Davis'],
        'email': ['john@example.com', 'jane@example.com', 'bob@example.com', 'alice@example.com', 'charlie@example.com'],
        'signup_date': ['2023-01-15', '2023-02-20', '2023-03-10', '2023-04-05', '2023-05-12']
    })
    
    # Create orders table
    orders_df = pd.DataFrame({
        'order_id': [101, 102, 103, 104, 105, 106, 107],
        'customer_id': [1, 2, 1, 3, 2, 4, 1],
        'order_date': ['2023-06-10', '2023-06-15', '2023-06-20', '2023-06-25', '2023-07-01', '2023-07-05', '2023-07-10'],
        'total_amount': [150.50, 200.75, 50.25, 300.00, 175.50, 220.25, 90.00]
    })
    
    # Create products table
    products_df = pd.DataFrame({
        'product_id': [1001, 1002, 1003, 1004, 1005],
        'name': ['Laptop', 'Smartphone', 'Tablet', 'Headphones', 'Monitor'],
        'category': ['Electronics', 'Electronics', 'Electronics', 'Accessories', 'Electronics'],
        'price': [1200.00, 800.00, 500.00, 150.00, 300.00]
    })
    
    # Create order_items table (junction table between orders and products)
    order_items_df = pd.DataFrame({
        'order_id': [101, 101, 102, 103, 104, 104, 105, 106, 107, 107],
        'product_id': [1001, 1004, 1002, 1003, 1001, 1005, 1002, 1003, 1004, 1005],
        'quantity': [1, 1, 1, 1, 1, 1, 1, 1, 2, 1],
        'item_price': [1200.00, 150.00, 800.00, 500.00, 1200.00, 300.00, 800.00, 500.00, 150.00, 300.00]
    })
    
    # Save dataframes to database
    customers_df.to_sql('customers', conn, index=False)
    orders_df.to_sql('orders', conn, index=False)
    products_df.to_sql('products', conn, index=False)
    order_items_df.to_sql('order_items', conn, index=False)
    
    print("Test database created successfully with tables: customers, orders, products, order_items")
    return "test_joins.db"

def create_test_data_dictionary(db_path):
    """Create a simple data dictionary for the test database."""
    # Create a data dictionary
    data_dict = {
        "dataset_name": "e-commerce",
        "description": "An e-commerce database with customers, orders, products, and order items.",
        "fields_count": 18,
        "customer_id": {
            "type": "integer",
            "description": "Unique identifier for customers",
            "relationships": ["orders.customer_id"]
        },
        "name": {
            "type": "text",
            "description": "Name of customer or product"
        },
        "email": {
            "type": "text",
            "description": "Customer email address"
        },
        "signup_date": {
            "type": "date",
            "description": "Date when customer signed up"
        },
        "order_id": {
            "type": "integer",
            "description": "Unique identifier for orders",
            "relationships": ["order_items.order_id"]
        },
        "order_date": {
            "type": "date",
            "description": "Date when order was placed"
        },
        "total_amount": {
            "type": "numeric",
            "description": "Total amount of the order"
        },
        "product_id": {
            "type": "integer",
            "description": "Unique identifier for products",
            "relationships": ["order_items.product_id"]
        },
        "category": {
            "type": "text",
            "description": "Product category"
        },
        "price": {
            "type": "numeric",
            "description": "Product price"
        },
        "quantity": {
            "type": "integer",
            "description": "Quantity of product in order"
        },
        "item_price": {
            "type": "numeric",
            "description": "Price of item in order"
        }
    }
    
    # Save to file
    import json
    with open("test_joins_data_dict.json", "w") as f:
        json.dump(data_dict, f, indent=2)
    
    print("Test data dictionary created successfully")
    return "test_joins_data_dict.json"

def test_direct_sql_joins(db_path):
    """Test SQL joins directly without using the OpenAI API."""
    print("\n===== TESTING DIRECT SQL JOINS =====\n")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Test SQL queries with joins
    test_queries = [
        # Simple join between customers and orders
        """
        SELECT c.name, o.order_id, o.order_date, o.total_amount 
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        ORDER BY c.name, o.order_date
        LIMIT 10
        """,
        
        # Multi-table join to find products ordered by a specific customer
        """
        SELECT c.name AS customer_name, p.name AS product_name, oi.quantity, o.order_date
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN products p ON oi.product_id = p.product_id
        WHERE c.name = 'John Smith'
        ORDER BY o.order_date
        """,
        
        # Aggregate query with joins
        """
        SELECT c.name, COUNT(o.order_id) AS order_count, SUM(o.total_amount) AS total_spent
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        GROUP BY c.name
        ORDER BY total_spent DESC
        """
    ]
    
    # Execute each query and print results
    for i, query in enumerate(test_queries):
        print(f"\n----- Query {i+1} -----")
        print(f"SQL: {query.strip()}\n")
        
        try:
            cursor.execute(query)
            results = [dict(row) for row in cursor.fetchall()]
            
            print(f"Results ({len(results)} rows):")
            for j, row in enumerate(results[:5]):
                print(f"  {j+1}. {row}")
            if len(results) > 5:
                print(f"  ... and {len(results) - 5} more rows")
        except Exception as e:
            print(f"Error executing query: {str(e)}")
    
    # Close connection
    conn.close()

def test_join_detection(processor, query):
    """Test the join detection functionality."""
    print(f"\n===== TESTING JOIN DETECTION =====\n")
    print(f"Query: {query}")
    
    # Get all tables
    tables = processor._get_all_tables()
    print(f"Available tables: {', '.join(tables)}")
    
    # Get schema for each table
    table_schemas = {}
    for table in tables:
        table_schemas[table] = processor._get_table_schema(table)
    
    # Test join detection
    might_need_join = processor._query_might_need_join(query, tables)
    print(f"Might need join: {might_need_join}")
    
    # Test join key identification
    join_keys = processor._identify_potential_join_keys(table_schemas)
    print("\nPotential join keys:")
    for key in join_keys:
        print(f"  - {key}")
    
    # If OpenAI API key is available, test join analysis
    try:
        join_analysis = processor._analyze_join_requirements(query, tables, table_schemas)
        if join_analysis:
            print("\nJoin analysis:")
            print(f"  Relevant tables: {', '.join(join_analysis.get('relevant_tables', []))}")
            print(f"  Requires join: {join_analysis.get('requires_join', False)}")
            print(f"  Summary: {join_analysis.get('summary', 'No summary provided.')}")
            
            if join_analysis.get('join_recommendations'):
                print("\nRecommended joins:")
                for rec in join_analysis['join_recommendations']:
                    print(f"  - {rec}")
        else:
            print("\nNo join analysis available (single table or API error)")
    except Exception as e:
        print(f"\nError in join analysis: {str(e)}")

if __name__ == "__main__":
    # Create test database and data dictionary
    db_path = create_test_database()
    data_dict_path = create_test_data_dictionary(db_path)
    
    # Test direct SQL joins
    test_direct_sql_joins(db_path)
    
    # Initialize processor
    try:
        processor = AgenticQueryProcessor(
            data_dict_path=data_dict_path,
            db_path=db_path
        )
        
        # Test join detection with different queries
        test_queries = [
            "List all customers and their orders",
            "Show me the total amount spent by each customer",
            "Which products were ordered by John Smith?",
            "Find customers who have ordered electronics products",
            "What is the most popular product category by order count?"
        ]
        
        for query in test_queries:
            test_join_detection(processor, query)
        
        # Clean up
        processor.close()
        
    except Exception as e:
        print(f"Error initializing processor: {str(e)}")
        print("Make sure your OpenAI API key is set in the .env file")
