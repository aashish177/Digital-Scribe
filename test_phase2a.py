"""
Test script for Phase 2A: Error Handling and Logging

This script tests the new error handling and logging infrastructure.
"""

import sys
import os

# Setup logging first
from logging_config import setup_logging, get_log_level_from_env, get_log_format_from_env, get_log_dir_from_env
from config import Config

# Configure logging
setup_logging(
    log_dir=get_log_dir_from_env(),
    level=get_log_level_from_env(),
    format_type=get_log_format_from_env()
)

import logging
from graph.workflow import create_content_workflow, initialize_state
from datetime import datetime

logger = logging.getLogger(__name__)

def test_successful_pipeline():
    """Test a successful pipeline run with logging."""
    print("\n" + "="*60)
    print("TEST 1: Successful Pipeline with Logging")
    print("="*60 + "\n")
    
    logger.info("Starting successful pipeline test")
    
    # Create workflow
    app = create_content_workflow()
    
    # Initialize state with tracking
    initial_state = initialize_state(
        content_request="Write a brief guide about the benefits of green tea",
        settings={"word_count": 500, "tone": "informative"}
    )
    
    logger.info(
        f"Running pipeline with request ID: {initial_state['request_id']}",
        extra={"extra_data": {"request": initial_state['content_request']}}
    )
    
    try:
        # Run the workflow
        result = app.invoke(initial_state)
        
        # Log results
        logger.info("Pipeline completed successfully")
        logger.info(
            "Execution times",
            extra={"extra_data": result.get("execution_times", {})}
        )
        
        print("\n✅ Pipeline completed successfully!")
        print(f"Request ID: {result.get('request_id', 'N/A')}")
        print(f"Started at: {result.get('started_at', 'N/A')}")
        print("\nExecution Times:")
        for agent, duration in result.get("execution_times", {}).items():
            print(f"  - {agent}: {duration:.2f}s")
        
        if result.get("errors"):
            print(f"\n⚠️  Errors encountered: {len(result['errors'])}")
            for error in result["errors"]:
                print(f"  - {error}")
        
        print(f"\n📝 Final content preview:")
        final_content = result.get("final_content", "")
        print(final_content[:200] + "..." if len(final_content) > 200 else final_content)
        
        return True
        
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
        print(f"\n❌ Pipeline failed: {str(e)}")
        return False


def test_error_handling():
    """Test error handling with invalid API key."""
    print("\n" + "="*60)
    print("TEST 2: Error Handling (Invalid API Key)")
    print("="*60 + "\n")
    
    logger.info("Starting error handling test")
    
    # Temporarily save the real API key
    real_key = Config.OPENAI_API_KEY
    
    try:
        # Set invalid API key
        Config.OPENAI_API_KEY = "invalid_key_for_testing"
        os.environ["OPENAI_API_KEY"] = "invalid_key_for_testing"
        
        # Create workflow
        app = create_content_workflow()
        
        # Initialize state
        initial_state = initialize_state(
            content_request="Test error handling"
        )
        
        logger.info("Running pipeline with invalid API key (expect errors)")
        
        try:
            result = app.invoke(initial_state)
            
            if result.get("errors"):
                print(f"\n✅ Errors were properly caught and logged!")
                print(f"Errors: {len(result['errors'])}")
                for error in result["errors"]:
                    print(f"  - {error}")
                return True
            else:
                print("\n⚠️  No errors were captured (unexpected)")
                return False
                
        except Exception as e:
            logger.info(f"Exception raised (expected): {type(e).__name__}")
            print(f"\n✅ Exception properly raised: {type(e).__name__}")
            print(f"Message: {str(e)}")
            return True
            
    finally:
        # Restore real API key
        Config.OPENAI_API_KEY = real_key
        os.environ["OPENAI_API_KEY"] = real_key


def test_logging_output():
    """Test that logs are being written to files."""
    print("\n" + "="*60)
    print("TEST 3: Log File Output")
    print("="*60 + "\n")
    
    log_dir = Config.LOG_DIR
    log_file = os.path.join(log_dir, "content_generation.log")
    error_log_file = os.path.join(log_dir, "errors.log")
    
    print(f"Checking log directory: {log_dir}")
    
    if os.path.exists(log_file):
        file_size = os.path.getsize(log_file)
        print(f"✅ Main log file exists: {log_file}")
        print(f"   Size: {file_size} bytes")
        
        # Show last few lines
        with open(log_file, 'r') as f:
            lines = f.readlines()
            print(f"   Total lines: {len(lines)}")
            print("\n   Last 3 log entries:")
            for line in lines[-3:]:
                print(f"   {line.strip()}")
    else:
        print(f"❌ Main log file not found: {log_file}")
    
    if os.path.exists(error_log_file):
        file_size = os.path.getsize(error_log_file)
        print(f"\n✅ Error log file exists: {error_log_file}")
        print(f"   Size: {file_size} bytes")
    else:
        print(f"\n⚠️  Error log file not found (may not have errors yet)")
    
    return os.path.exists(log_file)


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("PHASE 2A: ERROR HANDLING & LOGGING TESTS")
    print("="*60)
    
    # Validate config
    try:
        Config.validate()
    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        print("Please set OPENAI_API_KEY in your .env file")
        return
    
    results = []
    
    # Run tests
    results.append(("Successful Pipeline", test_successful_pipeline()))
    results.append(("Error Handling", test_error_handling()))
    results.append(("Log File Output", test_logging_output()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    total_passed = sum(1 for _, passed in results if passed)
    print(f"\nTotal: {total_passed}/{len(results)} tests passed")
    
    print(f"\n📁 Log files location: {Config.LOG_DIR}")
    print("   - content_generation.log (all logs)")
    print("   - errors.log (errors only)")


if __name__ == "__main__":
    main()
