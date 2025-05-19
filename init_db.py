# init_db.py
from db.db_utils import initialize_db

if __name__ == "__main__":
    # Initialize simulation DB
    initialize_db(simulation=True)
    # (Optional) Initialize backtest DB if you use it
    # initialize_db(simulation=False)
    print("Database initialized successfully.")
