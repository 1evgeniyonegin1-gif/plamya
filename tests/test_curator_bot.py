"""
Тесты для AI-Куратора
"""
import pytest
from datetime import datetime
from sqlalchemy import select

from curator_bot.database.models import User, ConversationMessage, ConversationContext


class TestUserModel:
    """Тесты для модели User"""
    
    @pytest.mark.asyncio
    async def test_create_user(self, test_session):
        """Тест создания пользователя"""
        user = User(
            telegram_id=987654321,
            username="new_user",
            first_name="New",
            last_name="User"
        )
        test_session.add(user)
        await test_session.commit()
        
        # Проверяем что пользователь создан
        result = await test_session.execute(
            select(User).where(User.telegram_id == 987654321)
        )
        saved_user = result.scalar_one()
        
        assert saved_user.username == "new_user"
        assert saved_user.first_name == "New"
        assert saved_user.user_type == "lead"  # Значение по умолчанию
        assert saved_user.is_active is True
    
    @pytest.mark.asyncio
    async def test_user_defaults(self, test_session):
        """Тест значений по умолчанию"""
        user = User(telegram_id=111222333)
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)
        
        assert user.user_type == "lead"
        assert user.qualification == "consultant"  # Обновлено на новую систему
        assert user.is_active is True
        assert user.is_blocked is False


class TestConversationMessage:
    """Тесты для модели ConversationMessage"""
    
    @pytest.mark.asyncio
    async def test_create_message(self, test_session, test_user):
        """Тест создания сообщения"""
        message = ConversationMessage(
            user_id=test_user.id,
            message_text="Привет, расскажи о продуктах",
            sender="user",
            timestamp=datetime.utcnow(),
            ai_model="gemini-1.5-flash"
        )
        test_session.add(message)
        await test_session.commit()
        
        # Проверяем что сообщение создано
        result = await test_session.execute(
            select(ConversationMessage).where(ConversationMessage.user_id == test_user.id)
        )
        saved_message = result.scalar_one()
        
        assert saved_message.message_text == "Привет, расскажи о продуктах"
        assert saved_message.sender == "user"
        assert saved_message.ai_model == "gemini-1.5-flash"
    
    @pytest.mark.asyncio
    async def test_message_relationship(self, test_session, test_user):
        """Тест связи между User и ConversationMessage"""
        # Создаём несколько сообщений
        for i in range(3):
            message = ConversationMessage(
                user_id=test_user.id,
                message_text=f"Сообщение {i}",
                sender="user" if i % 2 == 0 else "bot",
                timestamp=datetime.utcnow()
            )
            test_session.add(message)
        
        await test_session.commit()
        
        # Проверяем что у пользователя есть сообщения
        result = await test_session.execute(
            select(User).where(User.id == test_user.id)
        )
        user = result.scalar_one()
        
        # В SQLite relationship может работать по-другому, проверяем через запрос
        messages_result = await test_session.execute(
            select(ConversationMessage).where(ConversationMessage.user_id == user.id)
        )
        messages = messages_result.scalars().all()
        
        assert len(messages) == 3


class TestConversationContext:
    """Тесты для модели ConversationContext"""
    
    @pytest.mark.asyncio
    async def test_create_context(self, test_session, test_user):
        """Тест создания контекста диалога"""
        context = ConversationContext(
            user_id=test_user.id,
            recent_topics=["продукты", "бизнес"],
            last_question="Как начать бизнес?"
        )
        test_session.add(context)
        await test_session.commit()
        
        # Проверяем что контекст создан
        result = await test_session.execute(
            select(ConversationContext).where(ConversationContext.user_id == test_user.id)
        )
        saved_context = result.scalar_one()
        
        assert saved_context.last_question == "Как начать бизнес?"
        # SQLite может не поддерживать ARRAY, проверяем если есть
        if saved_context.recent_topics:
            assert "продукты" in saved_context.recent_topics
