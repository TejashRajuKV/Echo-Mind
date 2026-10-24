#!/usr/bin/env python3
"""
RAG Integration Module for Echo Mind
Seamlessly integrates RAG capabilities with the main analysis engine
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

# Import existing modules
try:
    from rag_system import EchoMindRAG
    from api_updater import DataManager  # Fallback to API system if needed
    from real_time_sports import get_ipl_captain_info, verify_captain_claim  # Sports fallback
except ImportError as e:
    logging.warning(f"Some modules not available: {e}")

logger = logging.getLogger(__name__)

class EnhancedEchoMindAnalyzer:
    """
    Enhanced Echo Mind Analyzer with integrated RAG capabilities
    Combines real-time data retrieval, vector search, and AI analysis
    """
    
    def __init__(self, project_id: str = "echo-mind-472808", location: str = "asia-south1"):
        self.project_id = project_id
        self.location = location
        
        # Initialize RAG system
        try:
            self.rag_system = EchoMindRAG(project_id, location)
            self.rag_available = True
            logger.info("✅ RAG system initialized")
        except Exception as e:
            logger.error(f"RAG system initialization failed: {e}")
            self.rag_system = None
            self.rag_available = False
        
        # Initialize fallback systems
        try:
            self.data_manager = DataManager()
            self.api_fallback = True
            logger.info("✅ API fallback system available")
        except:
            self.data_manager = None
            self.api_fallback = False
            logger.warning("API fallback system not available")
        
        # Sports module fallback
        self.sports_fallback = True
        
        logger.info("🚀 Enhanced Echo Mind Analyzer ready!")

    def analyze_claim(self, claim: str, context: str = "", 
                     enable_rag: bool = True, enable_fallbacks: bool = True) -> Dict[str, Any]:
        """
        Analyze a claim using multiple data sources and AI reasoning
        
        Args:
            claim: The claim to analyze
            context: Additional context (optional)
            enable_rag: Whether to use RAG system
            enable_fallbacks: Whether to use fallback systems
        
        Returns:
            Comprehensive analysis result
        """
        
        analysis_result = {
            'claim': claim,
            'context': context,
            'timestamp': datetime.now().isoformat(),
            'analysis_methods': [],
            'sources_used': [],
            'confidence_scores': {},
            'final_verdict': None,
            'explanation': "",
            'fact_check_tips': [],
            'supporting_evidence': [],
            'contradicting_evidence': []
        }
        
        # Method 1: RAG-based analysis (Primary)
        if enable_rag and self.rag_available:
            try:
                rag_result = self.analyze_with_rag(claim, context)
                analysis_result['rag_analysis'] = rag_result
                analysis_result['analysis_methods'].append('RAG')
                analysis_result['confidence_scores']['rag'] = rag_result.get('confidence_score', 0)
                
                if rag_result.get('retrieved_sources'):
                    analysis_result['sources_used'].extend([
                        src['source'] for src in rag_result['retrieved_sources']
                    ])
                
                logger.info("✅ RAG analysis completed")
                
            except Exception as e:
                logger.error(f"RAG analysis failed: {e}")
                analysis_result['rag_error'] = str(e)
        
        # Method 2: Sports-specific analysis (if relevant)
        if self.is_sports_query(claim) and enable_fallbacks:
            try:
                sports_result = self.analyze_sports_claim(claim)
                if sports_result:
                    analysis_result['sports_analysis'] = sports_result
                    analysis_result['analysis_methods'].append('Sports')
                    analysis_result['confidence_scores']['sports'] = sports_result.get('confidence', 0)
                    
                    logger.info("✅ Sports analysis completed")
                
            except Exception as e:
                logger.error(f"Sports analysis failed: {e}")
        
        # Method 3: API-based fallback
        if enable_fallbacks and self.api_fallback:
            try:
                api_result = self.analyze_with_api_data(claim)
                if api_result:
                    analysis_result['api_analysis'] = api_result
                    analysis_result['analysis_methods'].append('API')
                    analysis_result['confidence_scores']['api'] = api_result.get('confidence', 0)
                    
                    logger.info("✅ API analysis completed")
                
            except Exception as e:
                logger.error(f"API analysis failed: {e}")
        
        # Synthesize final verdict
        final_result = self.synthesize_analysis(analysis_result)
        
        logger.info(f"Analysis complete. Methods used: {analysis_result['analysis_methods']}")
        return final_result

    def analyze_with_rag(self, claim: str, context: str = "") -> Dict[str, Any]:
        """Analyze claim using RAG system"""
        if not self.rag_available:
            return {'error': 'RAG system not available'}
        
        # Combine claim and context for better retrieval
        query = f"{claim} {context}".strip()
        
        # Get RAG response
        return self.rag_system.generate_rag_response(query)

    def analyze_sports_claim(self, claim: str) -> Optional[Dict[str, Any]]:
        """Analyze sports-specific claims"""
        if not self.sports_fallback:
            return None
        
        try:
            # Check if it's an IPL captain claim
            if any(keyword in claim.lower() for keyword in ['captain', 'ipl', 'rcb', 'csk', 'mi', 'kkr']):
                # Extract team name (simple heuristic)
                team_keywords = {
                    'rcb': 'RCB', 'royal challengers': 'RCB',
                    'csk': 'CSK', 'chennai': 'CSK',
                    'mi': 'MI', 'mumbai': 'MI',
                    'kkr': 'KKR', 'kolkata': 'KKR',
                    'dc': 'DC', 'delhi': 'DC',
                    'pbks': 'PBKS', 'punjab': 'PBKS',
                    'rr': 'RR', 'rajasthan': 'RR',
                    'srh': 'SRH', 'hyderabad': 'SRH'
                }
                
                team = None
                claim_lower = claim.lower()
                for keyword, team_name in team_keywords.items():
                    if keyword in claim_lower:
                        team = team_name
                        break
                
                if team:
                    # Get current captain info
                    captain_info = get_ipl_captain_info(team)
                    if captain_info:
                        # Verify the claim
                        verification = verify_captain_claim(claim)
                        
                        return {
                            'team': team,
                            'current_captain': captain_info['captain'],
                            'verification': verification,
                            'confidence': verification.get('confidence', 80),
                            'source': 'Real-time Sports Module',
                            'last_updated': captain_info.get('last_updated', 'N/A')
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Sports analysis error: {e}")
            return None

    def analyze_with_api_data(self, claim: str) -> Optional[Dict[str, Any]]:
        """Analyze claim using API data manager"""
        if not self.api_fallback:
            return None
        
        try:
            # Query the API database for relevant information
            context_data = self.data_manager.get_context_for_query(claim)
            
            if context_data:
                return {
                    'api_context': context_data,
                    'confidence': 70,
                    'source': 'API Data Manager',
                    'last_updated': context_data.get('timestamp', 'N/A')
                }
            
            return None
            
        except Exception as e:
            logger.error(f"API analysis error: {e}")
            return None

    def is_sports_query(self, text: str) -> bool:
        """Check if query is sports-related"""
        sports_keywords = [
            'cricket', 'ipl', 'captain', 'team', 'player', 'match', 
            'tournament', 'football', 'olympics', 'sport', 'rcb', 'csk', 'mi'
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in sports_keywords)

    def synthesize_analysis(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize final verdict from multiple analysis methods"""
        
        # Collect verdicts and confidence scores
        verdicts = []
        confidence_scores = analysis_result['confidence_scores']
        
        # RAG verdict (highest priority)
        if 'rag_analysis' in analysis_result:
            rag_verdict = analysis_result['rag_analysis'].get('classification', 'Unknown')
            rag_confidence = confidence_scores.get('rag', 0)
            verdicts.append({
                'method': 'RAG',
                'verdict': rag_verdict,
                'confidence': rag_confidence,
                'weight': 0.6  # Highest weight
            })
        
        # Sports verdict (high priority for sports queries)
        if 'sports_analysis' in analysis_result:
            sports_verdict = analysis_result['sports_analysis']['verification'].get('verdict', 'Unknown')
            sports_confidence = confidence_scores.get('sports', 0)
            verdicts.append({
                'method': 'Sports',
                'verdict': sports_verdict,
                'confidence': sports_confidence,
                'weight': 0.8 if self.is_sports_query(analysis_result['claim']) else 0.3
            })
        
        # API verdict (moderate priority)
        if 'api_analysis' in analysis_result:
            api_confidence = confidence_scores.get('api', 0)
            verdicts.append({
                'method': 'API',
                'verdict': 'Suspicious',  # API data is contextual, not definitive
                'confidence': api_confidence,
                'weight': 0.2
            })
        
        # Calculate weighted final verdict
        if verdicts:
            verdict_scores = {'Trustworthy': 0, 'Suspicious': 0, 'False': 0}
            total_weight = 0
            
            for v in verdicts:
                weight = v['weight'] * (v['confidence'] / 100)
                verdict_scores[v['verdict']] += weight
                total_weight += weight
            
            # Normalize scores
            if total_weight > 0:
                for key in verdict_scores:
                    verdict_scores[key] /= total_weight
            
            # Final verdict is highest scoring
            final_verdict = max(verdict_scores, key=verdict_scores.get)
            final_confidence = int(verdict_scores[final_verdict] * 100)
            
        else:
            final_verdict = 'Suspicious'
            final_confidence = 50
        
        # Build comprehensive explanation
        explanation_parts = []
        
        if 'rag_analysis' in analysis_result:
            explanation_parts.append(f"RAG Analysis: {analysis_result['rag_analysis'].get('explanation', 'N/A')}")
        
        if 'sports_analysis' in analysis_result:
            explanation_parts.append(f"Sports Data: {analysis_result['sports_analysis']['verification'].get('explanation', 'N/A')}")
        
        if 'api_analysis' in analysis_result:
            explanation_parts.append("Additional API context was considered in the analysis.")
        
        # Update final result
        analysis_result.update({
            'final_verdict': final_verdict,
            'final_confidence': final_confidence,
            'explanation': ' | '.join(explanation_parts),
            'verdict_breakdown': verdict_scores if 'verdict_scores' in locals() else {},
            'methods_used': len(analysis_result['analysis_methods']),
            'rag_enabled': self.rag_available,
            'fallbacks_available': self.api_fallback or self.sports_fallback
        })
        
        # Add fact-checking tips
        if 'rag_analysis' in analysis_result:
            tips = analysis_result['rag_analysis'].get('fact_check_tips', [])
            analysis_result['fact_check_tips'].extend(tips)
        
        # Add general tips
        analysis_result['fact_check_tips'].extend([
            "Cross-reference information with multiple reliable sources",
            "Check the publication date and author credentials",
            "Look for primary sources and official statements",
            "Be cautious of claims that seem too sensational"
        ])
        
        return analysis_result

    def update_knowledge_base(self) -> Dict[str, Any]:
        """Update all knowledge bases (RAG + API + Sports)"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'updates': {}
        }
        
        # Update RAG database
        if self.rag_available:
            try:
                rag_update = self.rag_system.daily_update()
                results['updates']['rag'] = rag_update
                logger.info("✅ RAG database updated")
            except Exception as e:
                results['updates']['rag'] = {'error': str(e)}
                logger.error(f"RAG update failed: {e}")
        
        # Update API data
        if self.api_fallback:
            try:
                api_update = self.data_manager.update_all_data()
                results['updates']['api'] = api_update
                logger.info("✅ API data updated")
            except Exception as e:
                results['updates']['api'] = {'error': str(e)}
                logger.error(f"API update failed: {e}")
        
        return results

    def get_system_status(self) -> Dict[str, Any]:
        """Get status of all subsystems"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'rag_system': {
                'available': self.rag_available,
                'status': 'Operational' if self.rag_available else 'Unavailable'
            },
            'api_fallback': {
                'available': self.api_fallback,
                'status': 'Operational' if self.api_fallback else 'Unavailable'
            },
            'sports_fallback': {
                'available': self.sports_fallback,
                'status': 'Operational' if self.sports_fallback else 'Unavailable'
            }
        }
        
        # Get RAG stats if available
        if self.rag_available:
            try:
                rag_stats = self.rag_system.get_database_stats()
                status['rag_system']['stats'] = rag_stats
            except:
                pass
        
        return status

# Convenience function for simple analysis
def analyze_claim_simple(claim: str, context: str = "") -> Dict[str, Any]:
    """
    Simple wrapper function for claim analysis
    
    Usage:
        from rag_integration import analyze_claim_simple
        result = analyze_claim_simple("Faf du Plessis is RCB captain")
    """
    analyzer = EnhancedEchoMindAnalyzer()
    return analyzer.analyze_claim(claim, context)

def main():
    """Main function for testing integrated system"""
    analyzer = EnhancedEchoMindAnalyzer()
    
    import sys
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'analyze':
            claim = sys.argv[2] if len(sys.argv) > 2 else "Faf du Plessis is the current captain of RCB"
            print(f"\n🔍 Analyzing claim: '{claim}'")
            
            result = analyzer.analyze_claim(claim)
            print("\n📊 Analysis Result:")
            print(json.dumps(result, indent=2, default=str))
            
        elif command == 'status':
            status = analyzer.get_system_status()
            print("\n📈 System Status:")
            print(json.dumps(status, indent=2, default=str))
            
        elif command == 'update':
            print("\n🔄 Updating all knowledge bases...")
            results = analyzer.update_knowledge_base()
            print("\n✅ Update Results:")
            print(json.dumps(results, indent=2, default=str))
            
        else:
            print("Usage: python rag_integration.py [analyze|status|update] [claim]")
    else:
        print("🤖 Enhanced Echo Mind Analyzer with RAG")
        print("Commands:")
        print("  python rag_integration.py analyze 'claim'  - Analyze a claim")
        print("  python rag_integration.py status          - System status")
        print("  python rag_integration.py update          - Update knowledge")

if __name__ == '__main__':
    main()