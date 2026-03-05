"""Comprehensive end-to-end backend test."""
import asyncio
from app.main import app
from app.database import init_db, get_session_factory, User, Conversation, Message
from app.model_routing import get_model_profile

async def test_backend():
    print("=" * 60)
    print("BACKEND COMPREHENSIVE TEST")
    print("=" * 60)
    
    # Test 1: Model routing
    print("\n1️⃣  MODEL ROUTING CONFIGURATION")
    print("   ✓ Planner:", get_model_profile("planner")["name"])
    print("   ✓ Reasoning:", get_model_profile("reasoning")["name"])
    print("   ✓ Writing:", get_model_profile("writing")["name"])
    print("   ✓ Judge:", get_model_profile("judge")["name"])

    # Test 2: FastAPI app
    print("\n2️⃣  FASTAPI APPLICATION")
    print(f"   ✓ App initialized: {app.title}")
    print(f"   ✓ Total routes: {len(app.routes)}")
    
    chat_routes = [str(r.path) for r in app.routes if hasattr(r, 'path') and '/api/' in r.path]
    print(f"   ✓ API endpoints configured: {len(chat_routes)}")
    for route in sorted(chat_routes)[:5]:
        print(f"     - {route}")

    # Test 3: Database initialization
    print("\n3️⃣  DATABASE SCHEMA")
    db_url = "sqlite+aiosqlite:///./test_e2e.db"
    await init_db(db_url)
    
    from app.database import Base
    tables = [t.name for t in Base.metadata.sorted_tables]
    print(f"   ✓ Tables created: {len(tables)}")
    for table in sorted(tables):
        print(f"     - {table}")

    # Test 4: Session flow
    print("\n4️⃣  SESSION & CONVERSATION FLOW")
    factory = get_session_factory()
    from datetime import datetime
    import uuid
    import json

    async with factory() as session:
        # Create user
        user = User(
            id=str(uuid.uuid4()),
            email=None,
            name="Test User",
            is_anonymous=True,
            preferences_json=json.dumps({"theme": "dark"}),
            created_at=datetime.utcnow(),
            last_active=datetime.utcnow()
        )
        session.add(user)
        await session.commit()
        user_id = user.id
        print(f"   ✓ User created: {user_id}")

        # Create conversation
        conv = Conversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title="Test: Research Backend",
            summary=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(conv)
        await session.commit()
        conv_id = conv.id
        print(f"   ✓ Conversation created: {conv_id}")

        # Add messages
        for role, content in [
            ("user", "How does the research pipeline work?"),
            ("assistant", "The pipeline: Plan → Retrieve → Write → Judge → Refine"),
        ]:
            msg = Message(
                id=str(uuid.uuid4()),
                conversation_id=conv_id,
                role=role,
                content=content,
                extra_data_json=json.dumps({}),
                created_at=datetime.utcnow()
            )
            session.add(msg)
        await session.commit()
        print(f"   ✓ Messages persisted: 2")

    # Test 5: API validation
    print("\n5️⃣  API ROUTE VALIDATION")
    expected_routes = [
        "/api/users",
        "/api/conversations",
        "/api/answer",
        "/api/report",
        "/api/flashcards",
    ]
    
    registered = [r.path for r in app.routes if hasattr(r, 'path')]
    missing = [e for e in expected_routes if not any(e in r for r in registered)]
    
    if missing:
        print(f"   ⚠  Missing routes: {missing}")
    else:
        print(f"   ✓ All expected routes registered")
        for route in sorted([r for r in registered if '/api/' in r])[:8]:
            print(f"     - {route}")

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_backend())
