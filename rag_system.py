#!/usr/bin/env python3
"""
RAG (Retrieval-Augmented Generation) System for Echo Mind
Implements Vector Database + Vertex AI Embeddings + Real-time Document Retrieval
"""

import os
import json
import time
import sqlite3
import logging
import requests
import feedparser
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from google.cloud import aiplatform
import vertexai
from vertexai.generative_models import GenerativeModel
from vertexai.language_models import TextEmbeddingModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rag_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class Document:
    id: str
    text: str
    embedding: List[float]
    metadata: Dict[str, Any]
    timestamp: datetime
    source: str

@dataclass
class RetrievalResult:
    document: Document
    similarity_score: float

class EchoMindRAG:
    def __init__(self, project_id: str = "echo-mind-472808", location: str = "asia-south1"):
        self.project_id = project_id
        self.location = location
        self.vector_db_path = "echo_mind_vector.db"
        
        # Initialize Vertex AI
        aiplatform.init(project=project_id, location=location)
        vertexai.init(project=project_id, location=location)
        
        # Initialize models
        self.embedding_model = TextEmbeddingModel.from_pretrained("textembedding-gecko@003")
        self.generator_model = GenerativeModel("gemini-2.5-pro")
        
        # Initialize vector database
        self.init_vector_db()
        
        # News sources for daily updates
        self.news_sources = {
            'The Hindu': 'https://www.thehindu.com/news/feeder/default.rss',
            'India Today': 'https://www.indiatoday.in/rss/1206578',
            'Times of India': 'https://timesofindia.indiatimes.com/rssfeedstopstories.cms',
            'Indian Express': 'https://indianexpress.com/section/india/feed/',
            'NDTV': 'https://feeds.feedburner.com/NDTV-LatestNews',
            'BBC': 'http://feeds.bbci.co.uk/news/rss.xml',
            'Reuters': 'http://feeds.reuters.com/reuters/topNews'
        }
        
        logger.info(f"✅ RAG System initialized for project: {project_id}")

    def init_vector_db(self):
        """Initialize SQLite vector database with embedding storage"""
        conn = sqlite3.connect(self.vector_db_path)
        cursor = conn.cursor()
        
        # Create documents table with vector storage
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                embedding BLOB NOT NULL,  -- Store as binary blob
                metadata TEXT NOT NULL,   -- JSON string
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                source TEXT NOT NULL,
                category TEXT,
                url TEXT,
                title TEXT,
                summary TEXT
            )
        ''')
        
        # Create index for faster similarity searches
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp ON documents(timestamp DESC)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_category ON documents(category)
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Vector database initialized")

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using Vertex AI"""
        try:
            # Clean and truncate text if too long
            text = text.strip()[:8000]  # Vertex AI embedding limit
            
            embeddings = self.embedding_model.get_embeddings([text])
            return embeddings[0].values
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * 768  # Standard embedding dimension

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)
            
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return dot_product / (norm1 * norm2)
            
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0

    def store_document(self, text: str, metadata: Dict[str, Any], source: str, 
                      category: str = None, url: str = None, title: str = None) -> str:
        """Store document with embedding in vector database"""
        try:
            # Generate unique ID
            doc_id = f"{source}_{int(time.time())}_{hash(text[:100]) % 10000}"
            
            # Generate embedding
            embedding = self.generate_embedding(text)
            
            # Convert embedding to binary
            embedding_blob = np.array(embedding, dtype=np.float32).tobytes()
            
            # Create summary (first 200 chars)
            summary = text[:200] + "..." if len(text) > 200 else text
            
            # Store in database
            conn = sqlite3.connect(self.vector_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO documents 
                (id, text, embedding, metadata, source, category, url, title, summary, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                doc_id,
                text,
                embedding_blob,
                json.dumps(metadata),
                source,
                category,
                url,
                title,
                summary,
                datetime.now()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Stored document: {doc_id} from {source}")
            return doc_id
            
        except Exception as e:
            logger.error(f"Error storing document: {e}")
            return None

    def retrieve_similar_documents(self, query: str, top_k: int = 5, 
                                 category: str = None, days_back: int = 30) -> List[RetrievalResult]:
        """Retrieve most similar documents from vector database"""
        try:
            # Generate query embedding
            query_embedding = self.generate_embedding(query)
            
            # Fetch documents from database
            conn = sqlite3.connect(self.vector_db_path)
            cursor = conn.cursor()
            
            # Build query with optional filters
            sql_query = '''
                SELECT id, text, embedding, metadata, timestamp, source, category, url, title, summary
                FROM documents 
                WHERE timestamp > datetime('now', '-{} days')
            '''.format(days_back)
            
            if category:
                sql_query += f" AND category = '{category}'"
            
            sql_query += " ORDER BY timestamp DESC"
            
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            conn.close()
            
            # Calculate similarities
            results = []
            for row in rows:
                doc_id, text, embedding_blob, metadata_str, timestamp, source, cat, url, title, summary = row
                
                # Convert binary back to embedding
                try:
                    embedding = np.frombuffer(embedding_blob, dtype=np.float32).tolist()
                    similarity = self.cosine_similarity(query_embedding, embedding)
                    
                    if similarity > 0.3:  # Minimum relevance threshold
                        doc = Document(
                            id=doc_id,
                            text=text,
                            embedding=embedding,
                            metadata=json.loads(metadata_str),
                            timestamp=datetime.fromisoformat(timestamp),
                            source=source
                        )
                        
                        results.append(RetrievalResult(doc, similarity))
                        
                except Exception as e:
                    logger.warning(f"Error processing document {doc_id}: {e}")
                    continue
            
            # Sort by similarity and return top_k
            results.sort(key=lambda x: x.similarity_score, reverse=True)
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return []

    def fetch_and_store_news(self) -> int:
        """Fetch latest news and store in vector database"""
        stored_count = 0
        
        for source_name, rss_url in self.news_sources.items():
            try:
                logger.info(f"Fetching news from {source_name}")
                
                feed = feedparser.parse(rss_url)
                
                for entry in feed.entries[:10]:  # Latest 10 articles
                    try:
                        # Extract article data
                        title = entry.get('title', '')
                        description = entry.get('summary', entry.get('description', ''))
                        url = entry.get('link', '')
                        
                        # Combine title and description for embedding
                        text = f"{title}\n\n{description}"
                        
                        # Create metadata
                        metadata = {
                            'title': title,
                            'published': entry.get('published', ''),
                            'author': entry.get('author', ''),
                            'tags': [tag.get('term', '') for tag in entry.get('tags', [])]
                        }
                        
                        # Categorize news
                        category = self.categorize_news(text)
                        
                        # Store document
                        doc_id = self.store_document(
                            text=text,
                            metadata=metadata,
                            source=source_name,
                            category=category,
                            url=url,
                            title=title
                        )
                        
                        if doc_id:
                            stored_count += 1
                            
                    except Exception as e:
                        logger.warning(f"Error processing article from {source_name}: {e}")
                        continue
                
                # Rate limiting
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error fetching from {source_name}: {e}")
                continue
        
        logger.info(f"Stored {stored_count} new documents")
        return stored_count

    def categorize_news(self, text: str) -> str:
        """Categorize news based on content"""
        text_lower = text.lower()
        
        # Define category keywords
        categories = {
            'sports': ['cricket', 'football', 'ipl', 'olympics', 'player', 'match', 'tournament', 'captain', 'team'],
            'politics': ['government', 'minister', 'election', 'parliament', 'policy', 'bjp', 'congress', 'cm', 'pm'],
            'health': ['health', 'covid', 'vaccine', 'medical', 'hospital', 'disease', 'treatment', 'doctor'],
            'technology': ['tech', 'ai', 'software', 'app', 'internet', 'cyber', 'data', 'smartphone', 'computer'],
            'business': ['economy', 'market', 'stock', 'company', 'business', 'finance', 'investment', 'startup'],
            'entertainment': ['movie', 'film', 'bollywood', 'actor', 'music', 'celebrity', 'cinema', 'tv']
        }
        
        # Score each category
        category_scores = {}
        for category, keywords in categories.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                category_scores[category] = score
        
        # Return highest scoring category
        if category_scores:
            return max(category_scores, key=category_scores.get)
        else:
            return 'general'

    def generate_rag_response(self, user_query: str, max_context_length: int = 4000) -> Dict[str, Any]:
        """Generate response using RAG (Retrieve + Generate)"""
        try:
            # Step 1: Retrieve relevant documents
            logger.info(f"Retrieving documents for query: {user_query}")
            retrieved_docs = self.retrieve_similar_documents(user_query, top_k=5)
            
            if not retrieved_docs:
                logger.warning("No relevant documents found")
                return {
                    'response': 'No recent information found in knowledge base. Using general AI knowledge.',
                    'sources': [],
                    'confidence': 0.5
                }
            
            # Step 2: Build context from retrieved documents
            context_parts = []
            sources = []
            
            for result in retrieved_docs:
                doc = result.document
                context_parts.append(f"Source: {doc.source} (Similarity: {result.similarity_score:.3f})")
                context_parts.append(f"Date: {doc.timestamp.strftime('%Y-%m-%d')}")
                context_parts.append(f"Content: {doc.text[:800]}...")  # Truncate for context
                context_parts.append("---")
                
                sources.append({
                    'source': doc.source,
                    'timestamp': doc.timestamp.isoformat(),
                    'similarity': result.similarity_score,
                    'url': doc.metadata.get('url', ''),
                    'title': doc.metadata.get('title', '')
                })
            
            context = "\n".join(context_parts)
            
            # Truncate context if too long
            if len(context) > max_context_length:
                context = context[:max_context_length] + "...[truncated]"
            
            # Step 3: Generate response using Gemini with retrieved context
            prompt = f"""
You are Echo Mind, an AI fact-checker with access to recent information. Analyze the user's query using the provided context from recent news sources.

RECENT CONTEXT FROM VECTOR DATABASE:
{context}

USER QUERY: {user_query}

INSTRUCTIONS:
1. Use the retrieved context to provide accurate, up-to-date information
2. Cite specific sources from the context when making claims
3. If the query relates to information in the context, prioritize that over general knowledge
4. Classify the claim as Trustworthy, Suspicious, or False based on the evidence
5. Provide confidence score (0-100) based on quality of retrieved evidence
6. Give actionable fact-checking tips

RESPONSE FORMAT (JSON):
{{
    "classification": "Trustworthy|Suspicious|False",
    "confidence_score": 85,
    "explanation": "Detailed explanation using retrieved context...",
    "sources_used": ["Source1", "Source2"],
    "fact_check_tips": ["tip1", "tip2"],
    "retrieved_info_quality": "High|Medium|Low"
}}
"""
            
            # Generate response
            response = self.generator_model.generate_content(prompt)
            
            # Parse JSON response
            try:
                response_text = response.text.strip()
                if response_text.startswith("```json"):
                    response_text = response_text[7:].strip()
                if response_text.endswith("```"):
                    response_text = response_text[:-3].strip()
                
                result = json.loads(response_text)
                result['retrieved_sources'] = sources
                result['rag_enabled'] = True
                
                return result
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON response: {e}")
                return {
                    'response': response.text,
                    'sources': sources,
                    'confidence': 0.7,
                    'rag_enabled': True,
                    'error': 'JSON parsing failed'
                }
            
        except Exception as e:
            logger.error(f"Error generating RAG response: {e}")
            return {
                'response': f'Error in RAG system: {e}',
                'sources': [],
                'confidence': 0.0,
                'rag_enabled': False
            }

    def get_database_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector database"""
        try:
            conn = sqlite3.connect(self.vector_db_path)
            cursor = conn.cursor()
            
            # Total documents
            cursor.execute("SELECT COUNT(*) FROM documents")
            total_docs = cursor.fetchone()[0]
            
            # Documents by category
            cursor.execute("SELECT category, COUNT(*) FROM documents GROUP BY category")
            by_category = dict(cursor.fetchall())
            
            # Documents by source
            cursor.execute("SELECT source, COUNT(*) FROM documents GROUP BY source")
            by_source = dict(cursor.fetchall())
            
            # Recent documents (last 7 days)
            cursor.execute("SELECT COUNT(*) FROM documents WHERE timestamp > datetime('now', '-7 days')")
            recent_docs = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_documents': total_docs,
                'recent_documents': recent_docs,
                'by_category': by_category,
                'by_source': by_source,
                'database_path': self.vector_db_path
            }
            
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {'error': str(e)}

    def daily_update(self) -> Dict[str, Any]:
        """Perform daily RAG database update"""
        logger.info("Starting daily RAG update...")
        start_time = datetime.now()
        
        try:
            # Fetch and store new documents
            new_docs = self.fetch_and_store_news()
            
            # Clean old documents (optional - keep last 90 days)
            self.cleanup_old_documents(days_to_keep=90)
            
            # Get updated stats
            stats = self.get_database_stats()
            
            duration = (datetime.now() - start_time).seconds
            
            result = {
                'status': 'success',
                'new_documents_added': new_docs,
                'total_documents': stats.get('total_documents', 0),
                'duration_seconds': duration,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Daily RAG update completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error in daily update: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def cleanup_old_documents(self, days_to_keep: int = 90):
        """Remove old documents to keep database size manageable"""
        try:
            conn = sqlite3.connect(self.vector_db_path)
            cursor = conn.cursor()
            
            cursor.execute(f"DELETE FROM documents WHERE timestamp < datetime('now', '-{days_to_keep} days')")
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old documents")
                
        except Exception as e:
            logger.error(f"Error cleaning up old documents: {e}")

def main():
    """Main function for testing RAG system"""
    rag = EchoMindRAG()
    
    import sys
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'update':
            # Perform daily update
            result = rag.daily_update()
            print(json.dumps(result, indent=2))
            
        elif command == 'stats':
            # Show database statistics
            stats = rag.get_database_stats()
            print(json.dumps(stats, indent=2))
            
        elif command == 'query':
            # Test query
            query = sys.argv[2] if len(sys.argv) > 2 else "Who is the current captain of RCB?"
            print(f"\nTesting RAG with query: '{query}'")
            
            result = rag.generate_rag_response(query)
            print("\nRAG Response:")
            print(json.dumps(result, indent=2))
            
        else:
            print("Usage: python rag_system.py [update|stats|query 'your question']")
    else:
        print("Echo Mind RAG System")
        print("Commands:")
        print("  python rag_system.py update           - Update vector database")
        print("  python rag_system.py stats            - Show database stats")  
        print("  python rag_system.py query 'question' - Test RAG query")

if __name__ == '__main__':
    main()