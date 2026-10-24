import sqlite3
from pathlib import Path
from typing import List, Dict, Optional

# Database file path
DB_PATH = Path(__file__).parent / "factchecks.db"

def get_database_connection():
    """Get a connection to the SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    
    # Create table if it doesn't exist
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fact_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim TEXT NOT NULL,
            verdict TEXT NOT NULL,
            source TEXT NOT NULL,
            url TEXT,
            explanation TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    
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
        # Clean up words and remove common stop words
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'a', 'an'}
        search_terms = [word.replace("'", "").replace('"', '').replace(',', '') for word in words if len(word) > 2 and word.lower() not in stop_words]
        
        # Build dynamic query for better matching - prioritize multiple word matches
        query = """
        SELECT claim, verdict, source, url, explanation,
               CASE 
                   WHEN LOWER(claim) LIKE ? THEN 100  -- Exact phrase match
                   ELSE (
                       {} -- Multiple word match scoring
                   )
               END as relevance_score
        FROM fact_checks
        WHERE LOWER(claim) LIKE ? OR ({})
        ORDER BY relevance_score DESC, LENGTH(claim)
        LIMIT ?
        """
        
        # Parameters for exact phrase match
        exact_phrase = f"%{search_text.lower()}%"
        params = [exact_phrase, exact_phrase]
        
        # Build scoring for multiple words and conditions
        word_conditions = []
        word_scoring = []
        
        for i, term in enumerate(search_terms[:5]):  # Use up to 5 most relevant words
            word_conditions.append("LOWER(claim) LIKE ?")
            word_scoring.append(f"CASE WHEN LOWER(claim) LIKE ? THEN {10-i*2} ELSE 0 END")
            params.append(f"%{term}%")
            params.append(f"%{term}%")
        
        # Format the query with scoring logic
        if word_scoring:
            query = query.format(
                " + ".join(word_scoring),
                " OR ".join(word_conditions)
            )
        else:
            # Fallback if no good search terms
            query = """
            SELECT claim, verdict, source, url, explanation, 0 as relevance_score
            FROM fact_checks
            WHERE LOWER(claim) LIKE ?
            ORDER BY LENGTH(claim)
            LIMIT ?
            """
            params = [exact_phrase]
        
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


def search_fact_checks_structured(search_text: str, limit: int = 3) -> List[Dict]:
    """
    Structured version of search_fact_checks.
    Returns a list of dicts with keys: claim, verdict, source, url, explanation, created_at, type.
    Used by the evidence-trail builder in analysis_engine so callers get full metadata.
    """
    if not search_text or not search_text.strip():
        return []
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        words = search_text.lower().split()
        stop_words = {
            'the','and','or','but','in','on','at','to','for','of','with','by',
            'is','are','was','were','a','an'
        }
        search_terms = [
            w.replace("'", "").replace('"', '').replace(',', '')
            for w in words if len(w) > 2 and w.lower() not in stop_words
        ]
        if not search_terms:
            conn.close()
            return []

        # Build a relevance-scored query
        conditions = [f"LOWER(claim) LIKE ?" for _ in search_terms[:5]]
        scoring    = [f"CASE WHEN LOWER(claim) LIKE ? THEN {10 - i*2} ELSE 0 END"
                      for i, _ in enumerate(search_terms[:5])]
        params = []
        for t in search_terms[:5]:
            params.append(f"%{t}%")      # scoring params
        for t in search_terms[:5]:
            params.append(f"%{t}%")      # where params
        params.append(limit)

        query = f"""
            SELECT claim, verdict, source, url, explanation, created_at,
                   ({' + '.join(scoring)}) AS relevance_score
            FROM fact_checks
            WHERE {' OR '.join(conditions)}
            ORDER BY relevance_score DESC
            LIMIT ?
        """
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "claim":       row["claim"],
                "name":        f"{row['claim']} — {row['verdict']} ({row['source']})",
                "verdict":     row["verdict"],
                "source":      row["source"],
                "url":         row["url"] or "",
                "date":        (row["created_at"] or "")[:10],
                "explanation": row["explanation"] or "",
                "type":        "database_record",
            }
            for row in rows
        ]
    except Exception as exc:
        print(f"SQLite structured search error: {exc}")
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
        
def add_fact_check_to_database(fact_check_data: dict) -> bool:
    """
    Add a fact-check from auto-updater with enhanced data structure
    """
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # Check if this claim already exists (avoid duplicates)
        cursor.execute(
            "SELECT id FROM fact_checks WHERE LOWER(claim) = LOWER(?) AND source = ?",
            (fact_check_data['claim'], fact_check_data['source'])
        )
        existing = cursor.fetchone()
        
        if existing:
            print(f"Skipping duplicate: {fact_check_data['claim'][:50]}...")
            conn.close()
            return True
        
        # Insert new fact-check
        cursor.execute("""
            INSERT INTO fact_checks (claim, verdict, source, url, explanation)
            VALUES (?, ?, ?, ?, ?)
        """, (
            fact_check_data['claim'],
            fact_check_data['verdict'],
            fact_check_data['source'],
            fact_check_data.get('url', ''),
            fact_check_data.get('explanation', '')
        ))
        
        conn.commit()
        conn.close()
        print(f"[OK] Added: {fact_check_data['claim'][:50]}... - {fact_check_data['verdict']}")
        return True
        
    except Exception as e:
        print(f"Error adding fact-check to database: {e}")
        return False

def save_analysis_to_database(claim: str, analysis_result: dict) -> bool:
    """
    Save a user's claim and AI analysis result to the analysis_logs table.
    Keeps primary fact_checks table strictly for verified external institutions.
    """
    try:
        verdict = analysis_result.get("classification", "Unknown")
        explanation = analysis_result.get("explanation", "No explanation available.")
        score = analysis_result.get("score", 0)

        conn = get_database_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim TEXT NOT NULL,
                verdict TEXT NOT NULL,
                score INTEGER,
                explanation TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            INSERT INTO analysis_logs (claim, verdict, score, explanation)
            VALUES (?, ?, ?, ?)
        """, (claim, verdict, score, explanation))
        conn.commit()
        conn.close()
        safe_claim = claim[:50].encode('ascii', errors='replace').decode('ascii')
        print(f"[OK] Logged analysis: '{safe_claim}' - {verdict}")
        return True
    except Exception as e:
        print(f"Error saving analysis to log: {e}")
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

def initialize_sample_data():
    """Initialize database with some sample fact-check data including current political information"""
    sample_data = [
        {
            "claim": "COVID-19 vaccines contain microchips",
            "verdict": "False",
            "source": "WHO",
            "url": "https://www.who.int/emergencies/diseases/novel-coronavirus-2019/advice-for-public/mythbusters",
            "explanation": "COVID-19 vaccines do not contain microchips. This is a completely false conspiracy theory."
        },
        {
            "claim": "5G networks cause COVID-19",
            "verdict": "False",
            "source": "WHO",
            "url": "https://www.who.int/emergencies/diseases/novel-coronavirus-2019/advice-for-public/mythbusters",
            "explanation": "Viruses cannot spread through mobile networks. COVID-19 is spread through respiratory droplets."
        },
        {
            "claim": "Vitamin C prevents COVID-19",
            "verdict": "Mixed",
            "source": "Mayo Clinic",
            "url": "https://www.mayoclinic.org/diseases-conditions/coronavirus/in-depth/coronavirus-myths/art-20485720",
            "explanation": "While vitamin C supports immune function, there's no evidence it prevents COVID-19 specifically."
        },
        {
            "claim": "Jagan Mohan Reddy is the current CM of Andhra Pradesh",
            "verdict": "False",
            "source": "Election Commission of India",
            "url": "https://eci.gov.in/",
            "explanation": "As of June 2024, Chandrababu Naidu (TDP) is the Chief Minister of Andhra Pradesh. Jagan Mohan Reddy (YSRCP) lost the 2024 assembly elections."
        },
        {
            "claim": "Chandrababu Naidu is the current CM of Andhra Pradesh",
            "verdict": "Trustworthy",
            "source": "The Hindu",
            "url": "https://www.thehindu.com/news/national/andhra-pradesh/",
            "explanation": "Chandrababu Naidu of Telugu Desam Party (TDP) became the Chief Minister of Andhra Pradesh in June 2024 after winning the assembly elections."
        },
        {
            "claim": "TDP won Andhra Pradesh elections in 2024",
            "verdict": "Trustworthy",
            "source": "Election Commission of India",
            "url": "https://eci.gov.in/",
            "explanation": "The Telugu Desam Party (TDP) led by Chandrababu Naidu won the Andhra Pradesh assembly elections in 2024, defeating the incumbent YSRCP."
        }
    ]
    
    try:
        for item in sample_data:
            add_fact_check(
                claim=item["claim"],
                verdict=item["verdict"],
                source=item["source"],
                url=item["url"],
                explanation=item["explanation"]
            )
        print("[OK] Sample data initialized successfully")
        return True
    except Exception as e:
        print(f"Error initializing sample data: {e}")
        return False

if __name__ == "__main__":
    # Test the database functions
    print("🧪 Testing database functions...")
    
    # Check if database has data, if not initialize with sample data
    stats = get_database_stats()
    if stats.get('total_claims', 0) == 0:
        print("\n📝 Database is empty, initializing with sample data...")
        initialize_sample_data()
    
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
