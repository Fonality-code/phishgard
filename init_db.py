#!/usr/bin/env python3
"""
CLI script to initialize the database with RBAC
"""
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.utils.init_db import init_rbac, create_admin_user, assign_default_roles


def main():
    """Main function to initialize the database"""
    app = create_app()

    with app.app_context():
        print("Initializing database...")

        # Create all tables
        db.create_all()
        print("Database tables created.")

        # Initialize RBAC
        if init_rbac():
            print("RBAC system initialized.")
        else:
            print("Failed to initialize RBAC system.")
            return 1

        # Create admin user
        admin_email = input("Enter admin email (default: admin@example.com): ").strip()
        if not admin_email:
            admin_email = "admin@example.com"

        admin_password = input("Enter admin password (default: admin123): ").strip()
        if not admin_password:
            admin_password = "admin123"

        admin_user = create_admin_user(
            email=admin_email,
            password=admin_password,
            first_name="Admin",
            last_name="User"
        )

        if admin_user:
            print(f"Admin user created: {admin_email}")
        else:
            print("Failed to create admin user.")

        # Assign default roles to existing users
        assign_default_roles()

        print("\nDatabase initialization completed!")
        print(f"Admin credentials: {admin_email} / {admin_password}")
        print("You can now start the application with: python run.py")

        return 0


if __name__ == "__main__":
    sys.exit(main())
