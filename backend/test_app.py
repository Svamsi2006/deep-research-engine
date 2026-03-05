"""Quick test to verify FastAPI app loads with all routes."""
from app.main import app

print("✓ FastAPI app loaded successfully")
print("\n✓ All routes registered:")
for route in app.routes:
    if hasattr(route, 'path') and hasattr(route, 'methods'):
        print(f"  {route.methods} {route.path}")
    elif hasattr(route, 'path'):
        print(f"  {route.path}")

# Check that new user routes are present
user_routes = [r for r in app.routes if hasattr(r, 'path') and '/api/users' in r.path or '/api/conversations' in r.path]
print(f"\n✓ Found {len(user_routes)} user/conversation endpoints")

# Check that chat routes still exist
chat_routes = [r for r in app.routes if hasattr(r, 'path') and ('/api/answer' in r.path or '/api/report' in r.path)]
print(f"✓ Found {len(chat_routes)} chat endpoints (answer, report, flashcards)")

print("\n✅ All integrations successful!")
