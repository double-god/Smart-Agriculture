#!/usr/bin/env python3
"""
System Health Check Script for Smart Agriculture.

This script verifies that all infrastructure components are properly
configured and accessible.

Usage:
    python scripts/doctor.py

Exit codes:
    0: All checks passed
    1: One or more checks failed
"""

import os
import sys


# ANSI color codes for terminal output
class Colors:
    GREEN = "\033[92m"  # ✓
    RED = "\033[91m"    # ✗
    YELLOW = "\033[93m" # ⚠
    BLUE = "\033[94m"   # ℹ
    BOLD = "\033[1m"
    RESET = "\033[0m"


def print_success(message: str) -> None:
    """Print a success message with green checkmark."""
    print(f"{Colors.GREEN}✓{Colors.RESET} {message}")


def print_error(message: str) -> None:
    """Print an error message with red cross."""
    print(f"{Colors.RED}✗{Colors.RESET} {message}")


def print_warning(message: str) -> None:
    """Print a warning message with yellow warning sign."""
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {message}")


def print_info(message: str) -> None:
    """Print an info message with blue info sign."""
    print(f"{Colors.BLUE}ℹ{Colors.RESET} {message}")


def check_python_version() -> bool:
    """
    Check if Python version is exactly 3.12.

    Returns:
        bool: True if check passes
    """
    version = sys.version_info
    is_valid = version.major == 3 and version.minor == 12

    if is_valid:
        print_success(f"Python version: {version.major}.{version.minor}.{version.micro}")
    else:
        msg = f"Python version: {version.major}.{version.minor}.{version.micro} (expected 3.12.x)"
        print_error(msg)

    return is_valid


def check_postgresql() -> bool:
    """
    Check PostgreSQL database connection.

    Returns:
        bool: True if connection succeeds
    """
    try:
        # Try importing psycopg (sync) or asyncpg (async)
        import psycopg

        from app.core.config import get_settings

        settings = get_settings()

        # Parse connection string
        conn_string = settings.database_url

        # Simple connection test
        conn = psycopg.connect(conn_string)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        result = cursor.fetchone()
        if result:
            _ = result[0]
        conn.close()

        if '@' in settings.database_url:
            port = settings.database_url.split('@')[-1].split(':')[1].split('/')[0]
        else:
            port = "5432"

        print_success(f"PostgreSQL connection OK (port {port})")
        return True

    except ImportError:
        print_warning("PostgreSQL library not installed (psycopg or asyncpg)")
        return False
    except Exception as e:
        print_error(f"PostgreSQL connection failed: {str(e)}")
        return False


def check_redis() -> bool:
    """
    Check Redis connection using ping.

    Returns:
        bool: True if connection succeeds
    """
    try:
        import redis

        from app.core.config import get_settings

        settings = get_settings()

        # Parse Redis URL
        redis_url = settings.redis_url
        if redis_url.startswith("redis://"):
            # Extract host and port
            parsed = redis_url.replace("redis://", "").split(":")
            host = parsed[0]
            port = int(parsed[1].split("/")[0])
        else:
            host = "localhost"
            port = 6379

        # Test connection
        client = redis.Redis(host=host, port=port, decode_responses=True)
        client.ping()

        print_success(f"Redis connection OK ({host}:{port})")
        return True

    except ImportError:
        print_warning("Redis library not installed")
        return False
    except Exception as e:
        print_error(f"Redis connection failed: {str(e)}")
        return False


def check_chromadb() -> bool:
    """
    Check ChromaDB HTTP connection.

    Returns:
        bool: True if connection succeeds
    """
    try:
        import requests

        from app.core.config import get_settings

        settings = get_settings()

        # Test health endpoint
        url = f"http://{settings.chroma_host}:{settings.chroma_port}/api/v2/heartbeat"
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            print_success(f"ChromaDB connection OK ({settings.chroma_host}:{settings.chroma_port})")
            return True
        else:
            print_error(f"ChromaDB returned status {response.status_code}")
            return False

    except ImportError:
        print_warning("Requests library not installed")
        return False
    except requests.exceptions.RequestException as e:
        print_error(f"ChromaDB connection failed: {str(e)}")
        return False


def check_openai_api() -> bool:
    """
    Check OpenAI API key validity (optional check).

    Returns:
        bool: True if key is valid or not configured
    """
    try:
        from app.core.config import get_settings

        settings = get_settings()

        if not settings.openai_api_key or settings.openai_api_key.startswith("your-"):
            print_warning("OpenAI API key not configured (set OPENAI_API_KEY in .env)")
            return True  # Don't fail on optional check

        # Try a minimal API call
        import openai
        openai.api_key = settings.openai_api_key

        # Simple test: list models (very lightweight)
        _ = openai.OpenAI(api_key=settings.openai_api_key)
        # Don't actually make the API call to avoid charges, just validate key format
        if settings.openai_api_key.startswith("sk-"):
            print_success("OpenAI API key format valid")
            return True
        else:
            print_warning("OpenAI API key format may be invalid")
            return True  # Don't fail on optional check

    except ImportError:
        print_warning("OpenAI library not installed")
        return True  # Don't fail on optional check
    except Exception as e:
        print_warning(f"OpenAI API check skipped: {str(e)}")
        return True  # Don't fail on optional check


def check_project_structure() -> bool:
    """
    Check if required project directories exist.

    Returns:
        bool: True if all directories exist
    """
    required_dirs = [
        "app",
        "app/api",
        "app/core",
        "app/models",
        "app/services",
        "app/worker",
        "data",
        "scripts",
    ]

    all_exist = True
    for dir_path in required_dirs:
        if os.path.isdir(dir_path):
            print_success(f"Directory exists: {dir_path}/")
        else:
            print_error(f"Directory missing: {dir_path}/")
            all_exist = False

    return all_exist


def check_config_file() -> bool:
    """
    Check if .env file exists and .env.example is present.

    Returns:
        bool: True if config is properly set up
    """
    env_exists = os.path.exists(".env")
    env_example_exists = os.path.exists(".env.example")

    if env_exists:
        print_success(".env file exists")
    else:
        print_warning(".env file not found (copy from .env.example)")

    if env_example_exists:
        print_success(".env.example exists")
    else:
        print_error(".env.example missing")

    return env_example_exists


def main() -> int:
    """
    Run all health checks.

    Returns:
        int: Exit code (0 = success, 1 = failure)
    """
    print(f"\n{Colors.BOLD}🏥 Smart Agriculture System Health Check{Colors.RESET}\n")
    print(f"{Colors.BLUE}Checking infrastructure components...{Colors.RESET}\n")

    results = []

    # Run all checks
    results.append(("Python Version", check_python_version()))
    results.append(("Project Structure", check_project_structure()))
    results.append(("Config Files", check_config_file()))
    results.append(("PostgreSQL", check_postgresql()))
    results.append(("Redis", check_redis()))
    results.append(("ChromaDB", check_chromadb()))
    results.append(("OpenAI API", check_openai_api()))

    # Summary
    print(f"\n{Colors.BOLD}{'='*50}{Colors.RESET}")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    if all(result for _, result in results):
        msg = (
            f"{Colors.GREEN}{Colors.BOLD}✓ All systems operational! "
            f"({passed}/{total} checks passed){Colors.RESET}\n"
        )
        print(msg)
        return 0
    else:
        failed = total - passed
        msg = (
            f"{Colors.RED}{Colors.BOLD}✗ System has issues "
            f"({passed}/{total} checks passed, {failed} failed){Colors.RESET}\n"
        )
        print(msg)

        # Print failed checks
        print(f"{Colors.BOLD}Failed checks:{Colors.RESET}")
        for name, result in results:
            if not result:
                print(f"  {Colors.RED}✗{Colors.RESET} {name}")

        print()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
