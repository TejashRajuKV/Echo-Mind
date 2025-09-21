import sqlite3
from pathlib import Path
from typing import List, Dict, Optional

# Database file path
DB_PATH = Path(__file__).parent / "factchecks.db"

def get_database_connection():
    """Get a connection to the SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn

def search_fact_checks(search_text: str, limit: int = 3) -> List[str]:
    """
    Search for fact-checks related to the given text
    Returns formatted strings with claim, verdict, source, and URL
    """
    if not search_text or not search_text.strip():
        return []
    
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # Create search terms from the input text
        words = search_text.lower().split()
        search_terms = [word.replace("'", "").replace('"', '') for word in words[:3]]  # Use first 3 words
        
        # Build dynamic query for better matching
        query = """
        SELECT claim, verdict, source, url, explanation
        FROM fact_checks
        WHERE """
        
        conditions = []
        params = []
        
        for term in search_terms:
            conditions.append("LOWER(claim) LIKE ?")
            params.append(f"%{term}%")
        
        query += " OR ".join(conditions)
        query += " ORDER BY LENGTH(claim) LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Format results
        formatted_results = []
        for row in results:
            result = f"{row['claim']} — {row['verdict']} ({row['source']})"
            if row['url']:
                result += f" {row['url']}"
            formatted_results.append(result)
        
        conn.close()
        return formatted_results
        
    except Exception as e:
        print(f"SQLite search error: {e}")
        return []

def get_all_claims(limit: int = 10) -> List[Dict]:
    """Get all claims from the database for testing purposes"""
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, claim, verdict, source, url, explanation, created_at
            FROM fact_checks
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        
        results = cursor.fetchall()
        claims = [dict(row) for row in results]
        
        conn.close()
        return claims
        
    except Exception as e:
        print(f"Error fetching claims: {e}")
        return []

def add_fact_check(claim: str, verdict: str, source: str, url: str = None, explanation: str = None) -> bool:
    """Add a new fact-check to the database"""
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO fact_checks (claim, verdict, source, url, explanation)
            VALUES (?, ?, ?, ?, ?)
        """, (claim, verdict, source, url, explanation))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error adding fact-check: {e}")
        return False

def get_database_stats() -> Dict:
    """Get statistics about the database"""
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # Total count
        cursor.execute("SELECT COUNT(*) as total FROM fact_checks")
        total = cursor.fetchone()['total']
        
        # Count by verdict
        cursor.execute("""
            SELECT verdict, COUNT(*) as count 
            FROM fact_checks 
            GROUP BY verdict
        """)
        verdicts = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            'total_claims': total,
            'verdicts': verdicts,
            'database_path': str(DB_PATH),
            'database_exists': DB_PATH.exists()
        }
        
    except Exception as e:
        print(f"Error getting database stats: {e}")
        return {'error': str(e)}

if __name__ == "__main__":
    # Test the database functions
    print("🧪 Testing database functions...")
    
    # Test search
    print("\n🔍 Testing search function:")
    results = search_fact_checks("COVID vaccine", 2)
    for result in results:
        print(f"  • {result}")
    
    # Test stats
    print("\n📊 Database statistics:")
    stats = get_database_stats()
    print(f"  • Total claims: {stats.get('total_claims', 0)}")
    print(f"  • Database exists: {stats.get('database_exists', False)}")
    print(f"  • Verdicts: {stats.get('verdicts', {})}")