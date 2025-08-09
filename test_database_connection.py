#!/usr/bin/env python3
"""
Test script to verify Supabase database connection works with the provided credentials.
This will test the exact same connection logic used in the application.
"""

import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Set the environment variables (these should match Railway)
os.environ["SUPABASE_URL"] = "https://dacxljastlbykwqaivcm.supabase.co"
os.environ["SUPABASE_SERVICE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRhY3hsamFzdGxieWt3cWFpdmNtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1Mzk5Mzg4NSwiZXhwIjoyMDY5NTY5ODg1fQ.s5aJA-AzqvOU28hWkrnVWLXthSGpeSmCAUfl_wpcwQg"

# Import our settings after setting env vars
from src.config.settings import settings

async def test_database_connection():
    """Test the database connection using our application's logic."""
    
    print("🔍 Testing Database Connection...")
    print(f"📊 Supabase URL: {settings.supabase_url}")
    print(f"🔑 Service Key: {settings.supabase_service_key[:20]}...")
    print(f"🔗 Database URL: {settings.database_url}")
    
    try:
        # Create engine using our settings
        engine = create_async_engine(
            settings.database_url,
            echo=True,  # Show SQL queries
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        
        print("\n✅ Engine created successfully")
        
        # Test connection
        async with engine.begin() as conn:
            print("✅ Connection established")
            
            # Test basic query
            result = await conn.execute(text("SELECT 1 as test_connection"))
            row = result.fetchone()
            print(f"✅ Basic query successful: {row}")
            
            # Test our actual table
            result = await conn.execute(text("SELECT COUNT(*) as total_asins FROM simple_asin_status"))
            row = result.fetchone()
            print(f"✅ ASIN count query successful: {row[0]} ASINs in database")
            
            # Test a sample ASIN
            result = await conn.execute(text("SELECT asin, product_title FROM simple_asin_status LIMIT 3"))
            rows = result.fetchall()
            print(f"✅ Sample ASINs:")
            for row in rows:
                print(f"   - {row[0]}: {row[1] or 'No title yet'}")
        
        await engine.dispose()
        print("\n🎉 Database connection test SUCCESSFUL!")
        return True
        
    except Exception as e:
        print(f"\n❌ Database connection test FAILED: {e}")
        print(f"Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_database_connection())
    if success:
        print("\n✅ Your Railway database connection should work!")
    else:
        print("\n❌ Database connection needs fixing")
