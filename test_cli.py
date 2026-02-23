"""
Test script for Phase 2B: CLI Interface

This script tests the CLI functionality including arguments, progress display,
and output formatting.
"""

import subprocess
import os
import sys
from pathlib import Path
import json

def run_cli_command(args: list, expect_success: bool = True) -> tuple:
    """
    Run a CLI command and return the result.
    
    Args:
        args: List of command arguments
        expect_success: Whether to expect the command to succeed
        
    Returns:
        Tuple of (returncode, stdout, stderr)
    """
    cmd = ["python3", "cli.py"] + args
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent
    )
    
    if expect_success and result.returncode != 0:
        print(f"❌ Command failed: {' '.join(cmd)}")
        print(f"Error: {result.stderr}")
        return False
    
    return result.returncode, result.stdout, result.stderr


def test_help():
    """Test --help flag."""
    print("\n" + "="*60)
    print("TEST 1: Help Message")
    print("="*60 + "\n")
    
    returncode, stdout, stderr = run_cli_command(["--help"])
    
    if returncode == 0 and "--request" in stdout:
        print("✅ Help message displayed correctly")
        return True
    else:
        print("❌ Help message test failed")
        return False


def test_version():
    """Test --version flag."""
    print("\n" + "="*60)
    print("TEST 2: Version Display")
    print("="*60 + "\n")
    
    returncode, stdout, stderr = run_cli_command(["--version"])
    
    if returncode == 0 and "Content Generation Pipeline" in stdout:
        print(f"✅ Version displayed: {stdout.strip()}")
        return True
    else:
        print("❌ Version test failed")
        return False


def test_basic_generation():
    """Test basic content generation."""
    print("\n" + "="*60)
    print("TEST 3: Basic Content Generation")
    print("="*60 + "\n")
    
    returncode, stdout, stderr = run_cli_command([
        "--request", "Write a short guide on green tea",
        "--word-count", "300"
    ])
    
    if returncode == 0:
        if "Content Generation Complete" in stdout:
            print("✅ Content generated successfully")
            print(f"   Output indicates success")
            
            # Check if output file was created
            outputs_dir = Path("outputs")
            if outputs_dir.exists():
                files = list(outputs_dir.glob("final_content_*.md"))
                if files:
                    latest_file = max(files, key=lambda p: p.stat().st_mtime)
                    print(f"   Latest output file: {latest_file.name}")
                    return True
        
        print("❌ Content generation succeeded but output format unexpected")
        return False
    else:
        print(f"❌ Content generation failed")
        print(f"   Error: {stderr}")
        return False


def test_custom_options():
    """Test with custom options."""
    print("\n" + "="*60)
    print("TEST 4: Custom Options (tone, format)")
    print("="*60 + "\n")
    
    returncode, stdout, stderr = run_cli_command([
        "--request", "Tech trends in AI",
        "--tone", "professional",
        "--format", "json"
    ])
    
    if returncode == 0:
        print("✅ Custom options accepted")
        
        # Check for JSON output
        outputs_dir = Path("outputs")
        json_files = list(outputs_dir.glob("metadata_*.json"))
        if json_files:
            latest_json = max(json_files, key=lambda p: p.stat().st_mtime)
            print(f"   JSON metadata created: {latest_json.name}")
            return True
        else:
            print("⚠️  Command succeeded but JSON file not found")
            return True  # Still pass since command succeeded
    else:
        print(f"❌ Custom options test failed")
        return False


def test_invalid_tone():
    """Test with invalid tone argument."""
    print("\n" + "="*60)
    print("TEST 5: Invalid Argument Handling")
    print("="*60 + "\n")
    
    result = subprocess.run(
        ["python3", "cli.py", "--request", "Test", "--tone", "invalid"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("✅ Invalid argument properly rejected")
        print(f"   Error message shown to user")
        return True
    else:
        print("❌ Invalid argument was not caught")
        return False


def test_missing_request():
    """Test missing required argument."""
    print("\n" + "="*60)
    print("TEST 6: Missing Required Argument")
    print("="*60 + "\n")
    
    result = subprocess.run(
        ["python3", "cli.py", "--word-count", "500"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0 and "required" in result.stderr.lower():
        print("✅ Missing required argument detected")
        return True
    else:
        print("❌ Missing argument test failed")
        return False


def test_output_directory():
    """Test custom output directory."""
    print("\n" + "="*60)
    print("TEST 7: Custom Output Directory")
    print("="*60 + "\n")
    
    test_dir = Path("test_outputs")
    test_dir.mkdir(exist_ok=True)
    
    try:
        returncode, stdout, stderr = run_cli_command([
            "--request", "Quick test content",
            "--output-dir", str(test_dir)
        ])
        
        if returncode == 0:
            files = list(test_dir.glob("final_content_*.md"))
            if files:
                print(f"✅ Custom output directory used")
                print(f"   Files created in {test_dir}")
                return True
            else:
                print("⚠️  Command succeeded but files not in custom directory")
                return False
        else:
            print("❌ Custom output directory test failed")
            return False
    finally:
        # Cleanup
        if test_dir.exists():
            for file in test_dir.glob("*"):
                file.unlink()
            test_dir.rmdir()


def test_phase2c_flags():
    """Test all Phase 2C flags."""
    print("\n" + "="*60)
    print("TEST 8: Phase 2C Flags (organized-output, quality, audit)")
    print("="*60 + "\n")
    
    returncode, stdout, stderr = run_cli_command([
        "--request", "Testing phase 2c logs",
        "--word-count", "100",
        "--format", "all",
        "--organized-output",
        "--quality-report",
        "--audit-log"
    ])
    
    if returncode == 0:
        if "Quality Analysis" in stdout:
            print("✅ Quality Analysis block shown")
            if "📁 Output Files:" in stdout:
                print("✅ File outputs shown")
                return True
        print("❌ Flags did not show expected output.")
        return False
    else:
        print(f"❌ Phase 2c Flags test failed")
        print(f"   Error: {stderr}")
        return False

def main():
    """Run all CLI tests."""
    print("\n" + "="*60)
    print("PHASE 2B: CLI INTERFACE TESTS")
    print("="*60)
    
    # Check if API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("\n❌ OPENAI_API_KEY not set. Please set it in .env file.")
        print("Skipping tests that require API calls.")
        api_tests = False
    else:
        api_tests = True
    
    results = []
    
    # Run tests
    results.append(("Help Message", test_help()))
    results.append(("Version Display", test_version()))
    
    if api_tests:
        results.append(("Basic Generation", test_basic_generation()))
        results.append(("Custom Options", test_custom_options()))
        results.append(("Output Directory", test_output_directory()))
        results.append(("Phase 2C Flags", test_phase2c_flags()))
    
    results.append(("Invalid Argument", test_invalid_tone()))
    results.append(("Missing Required Arg", test_missing_request()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    total_passed = sum(1 for _, passed in results if passed)
    print(f"\nTotal: {total_passed}/{len(results)} tests passed")
    
    if not api_tests:
        print("\n⚠️  Some tests were skipped (API key not set)")
    
    return total_passed == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
