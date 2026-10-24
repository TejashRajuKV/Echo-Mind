#!/usr/bin/env python3
"""
Echo Mind RAG System Setup and Testing Script
Comprehensive setup, testing, and validation for the RAG implementation
"""

import os
import sys
import json
import time
import logging
import subprocess
from datetime import datetime
from typing import Dict, Any, List
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EchoMindRAGSetup:
    """Setup and testing class for Echo Mind RAG system"""
    
    def __init__(self):
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.setup_results = {
            'timestamp': datetime.now().isoformat(),
            'steps_completed': [],
            'errors': [],
            'warnings': []
        }
        
    def run_setup(self) -> Dict[str, Any]:
        """Run complete RAG system setup"""
        print("🚀 Starting Echo Mind RAG System Setup...")
        print("=" * 60)
        
        try:
            # Step 1: Check Python environment
            self.check_python_environment()
            
            # Step 2: Install dependencies
            self.install_dependencies()
            
            # Step 3: Check Google Cloud authentication
            self.check_gcp_auth()
            
            # Step 4: Test individual components
            self.test_components()
            
            # Step 5: Run integration tests
            self.test_integration()
            
            # Step 6: Initialize databases
            self.initialize_databases()
            
            # Step 7: Perform initial data update
            self.initial_data_update()
            
            # Step 8: Final validation
            self.final_validation()
            
            print("\n🎉 RAG System Setup Complete!")
            return self.setup_results
            
        except Exception as e:
            error_msg = f"Setup failed: {e}"
            logger.error(error_msg)
            self.setup_results['errors'].append(error_msg)
            print(f"\n❌ {error_msg}")
            traceback.print_exc()
            return self.setup_results

    def check_python_environment(self):
        """Check Python version and basic requirements"""
        print("\n1️⃣  Checking Python Environment...")
        
        # Check Python version
        python_version = sys.version_info
        if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
            raise Exception(f"Python 3.8+ required, found {python_version.major}.{python_version.minor}")
        
        print(f"   ✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        # Check if in virtual environment (recommended)
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            print("   ✅ Virtual environment detected")
        else:
            warning = "Virtual environment not detected - recommended for isolation"
            self.setup_results['warnings'].append(warning)
            print(f"   ⚠️  {warning}")
        
        self.setup_results['steps_completed'].append('python_environment')

    def install_dependencies(self):
        """Install required Python packages"""
        print("\n2️⃣  Installing Dependencies...")
        
        requirements_file = os.path.join(self.project_root, 'requirements_rag.txt')
        
        if not os.path.exists(requirements_file):
            print("   ⚠️  requirements_rag.txt not found, installing core packages manually")
            core_packages = [
                'google-cloud-aiplatform>=1.42.0',
                'vertexai>=1.42.0',
                'numpy>=1.24.0',
                'feedparser>=6.0.10',
                'requests>=2.28.0',
                'scikit-learn>=1.3.0'
            ]
            
            for package in core_packages:
                try:
                    subprocess.run([sys.executable, '-m', 'pip', 'install', package], 
                                 check=True, capture_output=True)
                    print(f"   ✅ Installed {package}")
                except subprocess.CalledProcessError as e:
                    error_msg = f"Failed to install {package}: {e}"
                    self.setup_results['errors'].append(error_msg)
                    print(f"   ❌ {error_msg}")
        else:
            try:
                print(f"   📦 Installing from {requirements_file}")
                result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', requirements_file], 
                                      capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    print("   ✅ All dependencies installed successfully")
                else:
                    print(f"   ❌ Some dependencies failed to install: {result.stderr}")
                    self.setup_results['warnings'].append(f"Dependency installation issues: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                warning = "Dependency installation timed out - some packages may not be installed"
                self.setup_results['warnings'].append(warning)
                print(f"   ⚠️  {warning}")
            except Exception as e:
                error_msg = f"Dependency installation failed: {e}"
                self.setup_results['errors'].append(error_msg)
                print(f"   ❌ {error_msg}")
        
        self.setup_results['steps_completed'].append('dependencies')

    def check_gcp_auth(self):
        """Check Google Cloud authentication"""
        print("\n3️⃣  Checking Google Cloud Authentication...")
        
        try:
            # Check if GOOGLE_APPLICATION_CREDENTIALS is set
            if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
                creds_file = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
                if os.path.exists(creds_file):
                    print(f"   ✅ Service account credentials found: {creds_file}")
                else:
                    warning = f"GOOGLE_APPLICATION_CREDENTIALS points to non-existent file: {creds_file}"
                    self.setup_results['warnings'].append(warning)
                    print(f"   ⚠️  {warning}")
            else:
                print("   ℹ️  GOOGLE_APPLICATION_CREDENTIALS not set - will try default credentials")
            
            # Try to import and initialize Vertex AI
            try:
                import vertexai
                from google.cloud import aiplatform
                
                # Initialize with project
                vertexai.init(project="echo-mind-472808", location="asia-south1")
                aiplatform.init(project="echo-mind-472808", location="asia-south1")
                
                print("   ✅ Vertex AI authentication successful")
                
            except Exception as e:
                error_msg = f"Vertex AI authentication failed: {e}"
                self.setup_results['errors'].append(error_msg)
                print(f"   ❌ {error_msg}")
                print("   ℹ️  You may need to run: gcloud auth application-default login")
        
        except ImportError as e:
            error_msg = f"Google Cloud libraries not available: {e}"
            self.setup_results['errors'].append(error_msg)
            print(f"   ❌ {error_msg}")
        
        self.setup_results['steps_completed'].append('gcp_auth')

    def test_components(self):
        """Test individual system components"""
        print("\n4️⃣  Testing Individual Components...")
        
        # Test RAG system
        print("   🧪 Testing RAG System...")
        try:
            from rag_system import EchoMindRAG
            rag = EchoMindRAG()
            
            # Test embedding generation
            test_text = "This is a test for embedding generation"
            embedding = rag.generate_embedding(test_text)
            
            if embedding and len(embedding) > 0:
                print("   ✅ RAG system initialized and embeddings working")
            else:
                print("   ❌ RAG system embedding generation failed")
                
        except Exception as e:
            error_msg = f"RAG system test failed: {e}"
            self.setup_results['errors'].append(error_msg)
            print(f"   ❌ {error_msg}")
        
        # Test sports module
        print("   🏏 Testing Sports Module...")
        try:
            from real_time_sports import get_ipl_captain_info, verify_captain_claim
            
            # Test captain info retrieval
            captain_info = get_ipl_captain_info("RCB")
            if captain_info:
                print(f"   ✅ Sports module working - RCB captain: {captain_info.get('captain', 'Unknown')}")
            else:
                print("   ⚠️  Sports module returned no data")
                
        except Exception as e:
            warning = f"Sports module test failed: {e}"
            self.setup_results['warnings'].append(warning)
            print(f"   ⚠️  {warning}")
        
        # Test API updater
        print("   🔄 Testing API Updater...")
        try:
            from api_updater import DataManager
            
            data_manager = DataManager()
            print("   ✅ API updater initialized successfully")
            
        except Exception as e:
            warning = f"API updater test failed: {e}"
            self.setup_results['warnings'].append(warning)
            print(f"   ⚠️  {warning}")
        
        self.setup_results['steps_completed'].append('component_tests')

    def test_integration(self):
        """Test integrated system"""
        print("\n5️⃣  Testing System Integration...")
        
        try:
            from rag_integration import EnhancedEchoMindAnalyzer
            
            analyzer = EnhancedEchoMindAnalyzer()
            
            # Test system status
            status = analyzer.get_system_status()
            print(f"   📊 System status: {json.dumps(status, indent=2, default=str)}")
            
            # Test simple claim analysis
            print("   🧪 Testing claim analysis...")
            test_claim = "The sky is blue"
            
            try:
                result = analyzer.analyze_claim(test_claim, enable_rag=True, enable_fallbacks=False)
                
                if result and 'final_verdict' in result:
                    print(f"   ✅ Integration test successful - Verdict: {result['final_verdict']}")
                    print(f"   📈 Methods used: {result.get('analysis_methods', [])}")
                else:
                    print("   ⚠️  Integration test returned incomplete results")
                    
            except Exception as e:
                warning = f"Claim analysis test failed: {e}"
                self.setup_results['warnings'].append(warning)
                print(f"   ⚠️  {warning}")
            
        except Exception as e:
            error_msg = f"Integration test failed: {e}"
            self.setup_results['errors'].append(error_msg)
            print(f"   ❌ {error_msg}")
        
        self.setup_results['steps_completed'].append('integration_tests')

    def initialize_databases(self):
        """Initialize vector and API databases"""
        print("\n6️⃣  Initializing Databases...")
        
        try:
            # Initialize RAG vector database
            from rag_system import EchoMindRAG
            rag = EchoMindRAG()
            
            # Check if database exists and get stats
            stats = rag.get_database_stats()
            print(f"   📊 Vector database stats: {stats}")
            
            if stats.get('total_documents', 0) == 0:
                print("   📝 Vector database is empty - ready for first data update")
            else:
                print(f"   ✅ Vector database has {stats.get('total_documents', 0)} documents")
            
        except Exception as e:
            error_msg = f"Database initialization failed: {e}"
            self.setup_results['errors'].append(error_msg)
            print(f"   ❌ {error_msg}")
        
        self.setup_results['steps_completed'].append('database_init')

    def initial_data_update(self):
        """Perform initial data population"""
        print("\n7️⃣  Initial Data Update...")
        
        try:
            from rag_system import EchoMindRAG
            rag = EchoMindRAG()
            
            print("   🔄 Fetching initial news data...")
            print("   ⏳ This may take a few minutes...")
            
            # Perform initial update with a few news sources
            update_result = rag.fetch_and_store_news()
            
            if update_result > 0:
                print(f"   ✅ Successfully stored {update_result} news articles")
                
                # Get updated stats
                stats = rag.get_database_stats()
                print(f"   📊 Database now contains {stats.get('total_documents', 0)} documents")
                print(f"   🏷️  Categories: {list(stats.get('by_category', {}).keys())}")
                
            else:
                warning = "No new documents were stored during initial update"
                self.setup_results['warnings'].append(warning)
                print(f"   ⚠️  {warning}")
                
        except Exception as e:
            error_msg = f"Initial data update failed: {e}"
            self.setup_results['errors'].append(error_msg)
            print(f"   ❌ {error_msg}")
            print("   ℹ️  You can run updates manually later with: python rag_system.py update")
        
        self.setup_results['steps_completed'].append('initial_data')

    def final_validation(self):
        """Final system validation with real query"""
        print("\n8️⃣  Final System Validation...")
        
        try:
            from rag_integration import EnhancedEchoMindAnalyzer
            
            analyzer = EnhancedEchoMindAnalyzer()
            
            # Test with a real-world sports claim
            test_claim = "Faf du Plessis is the current captain of RCB in IPL"
            print(f"   🧪 Testing with claim: '{test_claim}'")
            
            result = analyzer.analyze_claim(test_claim)
            
            if result:
                print(f"   🎯 Final Verdict: {result.get('final_verdict', 'Unknown')}")
                print(f"   🔢 Confidence: {result.get('final_confidence', 'N/A')}%")
                print(f"   📈 Methods used: {result.get('analysis_methods', [])}")
                print(f"   📚 Sources: {len(result.get('sources_used', []))}")
                
                if result.get('analysis_methods'):
                    print("   ✅ System validation successful!")
                else:
                    warning = "System validation completed but no analysis methods were used"
                    self.setup_results['warnings'].append(warning)
                    print(f"   ⚠️  {warning}")
            else:
                error_msg = "Final validation failed - no result returned"
                self.setup_results['errors'].append(error_msg)
                print(f"   ❌ {error_msg}")
                
        except Exception as e:
            error_msg = f"Final validation failed: {e}"
            self.setup_results['errors'].append(error_msg)
            print(f"   ❌ {error_msg}")
        
        self.setup_results['steps_completed'].append('final_validation')

    def print_setup_summary(self):
        """Print setup summary"""
        print("\n" + "="*60)
        print("📋 SETUP SUMMARY")
        print("="*60)
        
        print(f"✅ Steps Completed: {len(self.setup_results['steps_completed'])}")
        for step in self.setup_results['steps_completed']:
            print(f"   • {step}")
        
        if self.setup_results['warnings']:
            print(f"\n⚠️  Warnings: {len(self.setup_results['warnings'])}")
            for warning in self.setup_results['warnings']:
                print(f"   • {warning}")
        
        if self.setup_results['errors']:
            print(f"\n❌ Errors: {len(self.setup_results['errors'])}")
            for error in self.setup_results['errors']:
                print(f"   • {error}")
        
        print(f"\n🕐 Setup completed at: {self.setup_results['timestamp']}")
        
        # Save results to file
        results_file = os.path.join(self.project_root, 'setup_results.json')
        with open(results_file, 'w') as f:
            json.dump(self.setup_results, f, indent=2, default=str)
        print(f"📄 Setup results saved to: {results_file}")

def main():
    """Main setup function"""
    print("🤖 Echo Mind RAG System Setup")
    print("Version 1.0 - Retrieval-Augmented Generation")
    
    setup = EchoMindRAGSetup()
    results = setup.run_setup()
    setup.print_setup_summary()
    
    # Quick start guide
    print("\n🚀 QUICK START GUIDE")
    print("="*60)
    print("1. Test the system:")
    print("   python rag_integration.py analyze 'Your test claim here'")
    print("\n2. Check system status:")
    print("   python rag_integration.py status")
    print("\n3. Update knowledge base:")
    print("   python rag_integration.py update")
    print("\n4. Use in your code:")
    print("   from rag_integration import analyze_claim_simple")
    print("   result = analyze_claim_simple('Your claim here')")
    print("\n5. Schedule daily updates (recommended):")
    print("   Set up a cron job to run: python rag_system.py update")
    
    if len(results['errors']) == 0:
        print("\n🎉 Setup completed successfully! Your RAG system is ready to use.")
        return 0
    else:
        print(f"\n⚠️  Setup completed with {len(results['errors'])} errors. Please review and fix them.")
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)