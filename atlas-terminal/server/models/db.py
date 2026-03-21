"""Supabase database client for ATLAS Terminal."""
import os
from typing import Optional

# Supabase client (lazy init)
_supabase_client = None

def get_supabase():
    """Get or create Supabase client. Returns None if not configured."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        return None
    try:
        from supabase import create_client
        _supabase_client = create_client(url, key)
        return _supabase_client
    except ImportError:
        return None
