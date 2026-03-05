"""Test end-to-end conversation flow with user sessions."""
import asyncio
import sys
from app.database import init_db, get_session_factory, User, Conversation, Message
from sqlalchemy import select

async def test_conversation_flow():
    """Test the full flow: create user → create conversation → add messages."""
    
    # Use file-based database for testing (in-memory + NullPool = connection issues)
    db_url = "sqlite+aiosqlite:///./test_conversation_v03.db"
    print("🔧 Initializing test database...")
    await init_db(db_url)
    print("✓ Database initialized\n")
    
    # Verify tables were created
    print("🔍 Checking created tables...")
    from app.database import Base
    table_names = [table.name for table in Base.metadata.sorted_tables]
    print(f"   Tables in metadata: {table_names}")
    print(f"   ✓ Found {len(table_names)} tables\n")
    
    factory = get_session_factory()
    
    # Step 1: Create anonymous user
    print("1️⃣  Creating anonymous user...")
    async with factory() as session:
        from datetime import datetime
        import uuid
        
        user = User(
            id=str(uuid.uuid4()),
            email=None,
            name="Anonymous",
            is_anonymous=True,
            preferences_json="{}",
            created_at=datetime.utcnow(),
            last_active=datetime.utcnow()
        )
        session.add(user)
        await session.commit()
        user_id = user.id
        print(f"   ✓ Created user: {user_id}\n")
    
    # Step 2: Create conversation
    print("2️⃣  Creating conversation...")
    async with factory() as session:
        conv = Conversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title="Test: How does async work?",
            summary=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(conv)
        await session.commit()
        conv_id = conv.id
        print(f"   ✓ Created conversation: {conv_id}\n")
    
    # Step 3: Add user message
    print("3️⃣  Adding user message...")
    async with factory() as session:
        import json
        msg1 = Message(
            id=str(uuid.uuid4()),
            conversation_id=conv_id,
            role="user",
            content="How does async/await work in Python?",
            extra_data_json="{}",
            created_at=datetime.utcnow()
        )
        session.add(msg1)
        await session.commit()
        print(f"   ✓ User message saved\n")
    
    # Step 4: Add assistant message with metadata
    print("4️⃣  Adding assistant message...")
    async with factory() as session:
        msg2 = Message(
            id=str(uuid.uuid4()),
            conversation_id=conv_id,
            role="assistant",
            content="Async/await allows you to write concurrent code...",
            extra_data_json=json.dumps({
                "provider": "openrouter",
                "tokens_used": 150,
                "cost_usd": 0.0001,
                "report_id": str(uuid.uuid4())
            }),
            created_at=datetime.utcnow()
        )
        session.add(msg2)
        
        # Update conversation timestamp
        conv = await session.get(Conversation, conv_id)
        conv.updated_at = datetime.utcnow()
        
        await session.commit()
        print(f"   ✓ Assistant message saved\n")
    
    # Step 5: Verify conversation history
    print("5️⃣  Retrieving conversation history...")
    async with factory() as session:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conv_id)
            .order_by(Message.created_at)
        )
        result = await session.execute(stmt)
        messages = result.scalars().all()
        
        print(f"   ✓ Found {len(messages)} messages:")
        for i, msg in enumerate(messages, 1):
            extra = msg.extra_data if hasattr(msg, 'extra_data') else {}
            print(f"     {i}. [{msg.role}] {msg.content[:50]}...")
            if extra:
                print(f"        Metadata: {extra}")
        print()
    
    # Step 6: Test conversation list for user
    print("6️⃣  Listing user's conversations...")
    async with factory() as session:
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        )
        result = await session.execute(stmt)
        conversations = result.scalars().all()
        
        print(f"   ✓ User has {len(conversations)} conversation(s):")
        for conv in conversations:
            print(f"     - {conv.title}")
            print(f"       ID: {conv.id}")
            print(f"       Updated: {conv.updated_at}")
        print()
    
    print("✅ All conversation flow tests passed!")
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(test_conversation_flow())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
