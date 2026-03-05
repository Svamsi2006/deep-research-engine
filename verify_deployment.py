#!/usr/bin/env python3
"""
Pre-deployment verification script.
Checks all critical components before deployment.
"""

import sys
import subprocess
from pathlib import Path

def run_check(name: str, check_fn, fatal=False):
    """Run a single check and report results."""
    try:
        result = check_fn()
        if result:
            print(f"  ✅ {name}")
            return True
        else:
            print(f"  {'🔴' if fatal else '⚠️ '} {name}")
            return not fatal
    except Exception as e:
        print(f"  {'🔴' if fatal else '⚠️ '} {name}: {str(e)[:50]}")
        return not fatal


def main():
    print("=" * 70)
    print("DEEP RESEARCH AGENT - PRE-DEPLOYMENT VERIFICATION")
    print("=" * 70)
    
    all_passed = True
    
    # ────────────────────────────────────────────────────────────────────
    # Backend Checks
    # ────────────────────────────────────────────────────────────────────
    print("\n🐍 BACKEND CHECKS")
    print("-" * 70)
    
    backend_path = Path("backend")
    
    # Check Python files exist
    all_passed &= run_check(
        "Main app module",
        lambda: (backend_path / "app" / "main.py").exists(),
        fatal=True
    )
    
    all_passed &= run_check(
        "Database module",
        lambda: (backend_path / "app" / "database.py").exists(),
        fatal=True
    )
    
    all_passed &= run_check(
        "Chat routes",
        lambda: (backend_path / "app" / "routes" / "chat.py").exists(),
        fatal=True
    )
    
    all_passed &= run_check(
        "Users routes (V0.3)",
        lambda: (backend_path / "app" / "routes" / "users.py").exists(),
        fatal=True
    )
    
    all_passed &= run_check(
        "Model routing (V0.3)",
        lambda: (backend_path / "app" / "model_routing.py").exists(),
        fatal=True
    )
    
    all_passed &= run_check(
        "Error handling (V0.3)",
        lambda: (backend_path / "app" / "error_handling.py").exists(),
        fatal=True
    )
    
    # Check imports work
    def check_imports():
        try:
            from app.main import app
            from app.database import User, Conversation, Message
            from app.model_routing import get_model_profile
            from app.error_handling import APIError
            from app.routes.users import router
            return True
        except Exception as e:
            print(f"    Import error: {e}")
            return False
    
    all_passed &= run_check("Import validation", check_imports, fatal=True)
    
    # ────────────────────────────────────────────────────────────────────
    # Frontend Checks
    # ────────────────────────────────────────────────────────────────────
    print("\n⚛️  FRONTEND CHECKS")
    print("-" * 70)
    
    frontend_path = Path("frontend")
    
    all_passed &= run_check(
        "Package.json",
        lambda: (frontend_path / "package.json").exists(),
        fatal=True
    )
    
    all_passed &= run_check(
        "Main page component",
        lambda: (frontend_path / "src" / "app" / "page.tsx").exists(),
        fatal=True
    )
    
    all_passed &= run_check(
        "Session hook (V0.3)",
        lambda: (frontend_path / "src" / "lib" / "use-session.ts").exists(),
        fatal=True
    )
    
    all_passed &= run_check(
        "Error hook (V0.3)",
        lambda: (frontend_path / "src" / "lib" / "use-api-error.ts").exists(),
        fatal=True
    )
    
    all_passed &= run_check(
        "Conversation sidebar (V0.3)",
        lambda: (frontend_path / "src" / "components" / "conversation-sidebar.tsx").exists(),
        fatal=True
    )
    
    all_passed &= run_check(
        "Message history (V0.3)",
        lambda: (frontend_path / "src" / "components" / "message-history.tsx").exists(),
        fatal=True
    )
    
    # ────────────────────────────────────────────────────────────────────
    # Documentation Checks
    # ────────────────────────────────────────────────────────────────────
    print("\n📚 DOCUMENTATION")
    print("-" * 70)
    
    all_passed &= run_check(
        "README.md",
        lambda: Path("README.md").exists(),
        fatal=False
    )
    
    all_passed &= run_check(
        "Architecture documentation",
        lambda: Path("ARCHITECTURE_AND_HOW_IT_WORKS.md").exists(),
        fatal=False
    )
    
    all_passed &= run_check(
        "V0.3 implementation guide",
        lambda: Path("V03_IMPLEMENTATION_SUMMARY.md").exists(),
        fatal=False
    )
    
    all_passed &= run_check(
        "Implementation complete summary",
        lambda: Path("IMPLEMENTATION_COMPLETE.md").exists(),
        fatal=False
    )
    
    all_passed &= run_check(
        "Quick reference guide",
        lambda: Path("QUICK_REFERENCE.md").exists(),
        fatal=False
    )
    
    # ────────────────────────────────────────────────────────────────────
    # Deployment Files
    # ────────────────────────────────────────────────────────────────────
    print("\n🚀 DEPLOYMENT FILES")
    print("-" * 70)
    
    all_passed &= run_check(
        "Docker Dockerfile",
        lambda: (backend_path / "Dockerfile").exists(),
        fatal=False
    )
    
    all_passed &= run_check(
        "Docker Compose",
        lambda: Path("docker-compose.yml").exists(),
        fatal=False
    )
    
    all_passed &= run_check(
        ".env template",
        lambda: Path(".env.example").exists() or Path(".env").exists(),
        fatal=False
    )
    
    # ────────────────────────────────────────────────────────────────────
    # Summary
    # ────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    
    if all_passed:
        print("✅ PRE-DEPLOYMENT VERIFICATION PASSED")
        print("\n🎉 PROJECT IS READY FOR DEPLOYMENT!")
        print("\nNext steps:")
        print("  1. Set .env variables (OPENROUTER_API_KEY, GROQ_API_KEY, etc.)")
        print("  2. Backend: gunicorn app.main:app --workers 4")
        print("  3. Frontend: npm run build && npm run start")
        print("  4. Test: Visit http://localhost:3000")
        print("=" * 70)
        return 0
    else:
        print("❌ PRE-DEPLOYMENT VERIFICATION FAILED")
        print("\nFix the issues above and try again.")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
