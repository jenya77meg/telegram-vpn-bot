import pytest
import datetime
from datetime import timezone
from aiogram.utils.keyboard import InlineKeyboardMarkup

import tgbot.services.profile_service as svc

@pytest.mark.asyncio
async def test_active_paid_subscription(monkeypatch):
    # Действующая платная подписка (оставшихся дней больше 10) — кнопки продления нет
    future = (datetime.datetime.now(timezone.utc) + datetime.timedelta(days=20)).isoformat()
    record = {'sub_id': 'sub1', 'subscription_end': future, 'is_trial': False}
    async def dummy_get_user(uid):
        return record
    monkeypatch.setattr(svc, 'get_user', dummy_get_user)
    async def dummy_get_raw_link(sub):
        return 'link'
    monkeypatch.setattr(svc, 'get_raw_link', dummy_get_raw_link)

    text, inline_kb, reply_kb = await svc.build_profile_content(123)

    assert '🔸 Тип подписки: <b>платная</b>' in text
    # При большом количестве дней кнопки продления нет
    assert inline_kb is None
    assert reply_kb is not None
    assert reply_kb is not None

@pytest.mark.asyncio
async def test_near_expiry_paid(monkeypatch):
    # Осталось 5 дней — кнопка Продлить должна быть
    future = (datetime.datetime.now(timezone.utc) + datetime.timedelta(days=5)).isoformat()
    record = {'sub_id': 'sub1', 'subscription_end': future, 'is_trial': False}
    async def dummy_get_user(uid):
        return record
    monkeypatch.setattr(svc, 'get_user', dummy_get_user)
    async def dummy_get_raw_link(sub):
        return 'link'
    monkeypatch.setattr(svc, 'get_raw_link', dummy_get_raw_link)

    text, inline_kb, _ = await svc.build_profile_content(123)
    assert isinstance(inline_kb, InlineKeyboardMarkup)
    # Проверяем, что кнопка с callback_data 'vpn' есть среди кнопок
    buttons = [btn.callback_data for row in inline_kb.inline_keyboard for btn in row]
    assert 'vpn' in buttons

@pytest.mark.asyncio
async def test_expired_trial(monkeypatch):
    # Пробный истёк
    past = (datetime.datetime.now(timezone.utc) - datetime.timedelta(days=1)).isoformat()
    record = {'is_trial': True, 'trial_sub_id': 'trial1', 'trial_end': past}
    async def dummy_get_user(uid):
        return record
    monkeypatch.setattr(svc, 'get_user', dummy_get_user)
    async def dummy_clear_user_subscription(uid, trial=True):
        return None
    monkeypatch.setattr(svc, 'clear_user_subscription', dummy_clear_user_subscription)
    async def dummy_get_raw_link(sub):
        return 'link'
    monkeypatch.setattr(svc, 'get_raw_link', dummy_get_raw_link)

    text, inline_kb, _ = await svc.build_profile_content(123)
    assert '🔸 Тип подписки: <b>отсутствует</b>' in text
    assert inline_kb is None
