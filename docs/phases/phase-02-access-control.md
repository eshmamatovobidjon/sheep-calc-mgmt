# Phase 02 — Access Control and Bot Shell

| | |
|---|---|
| **Depends on** | 01 |
| **Can run in parallel with** | 03 |
| **Unblocks** | 04, 05 (they use the permission filter, menu and texts) |
| **Read first** | [AGENTS.md](../../AGENTS.md), [architecture.md](../architecture.md) sections 3, 5, 6 (`bot_user`), 9; [analysis-and-plan.md](../analysis-and-plan.md) 7.3 |

## Goal

Only approved users can use the bot. The admin approves access requests and manages two permissions per user: **Upload** (accountant) and **View** (reports). Every user sees a main menu with only the buttons they may use.

## Starting point

Phase 01 is done: DB with `bot_user`, admin seeded, `DbSessionMiddleware`, placeholder `/start`.

## Tasks

1. **`services/users.py`**: `get_by_telegram_id`, `create_pending(telegram_id, full_name, username)`, `set_permissions(user_id, can_upload, can_view)`, `set_status(user_id, status)`, `list_users()`, `has_permission(user, perm) -> bool` (admin → always true; otherwise `status == active` and the flag).
2. **`bot/middlewares.py`**: add `AuthMiddleware` that puts `user: BotUser | None` into handler data. It never creates users.
3. **`bot/filters.py`**: `Perm` enum (`UPLOAD`, `VIEW`, `ADMIN`) and `HasPermission(perm)` filter.
4. **`bot/texts.py`**: all strings for this phase, plus `BTN_*` constants for **every** menu button in architecture section 9 (later phases reuse them).
5. **`bot/keyboards.py`**: `main_menu(user)` reply keyboard:
   - Upload: Загрузить рейс, Шаблон, Оплата, Последние оплаты, Клиенты
   - View: Отчёты, Должники, Рейсы
   - Admin: Пользователи
   - `cancel_keyboard()` with a single "Отмена" button for dialogs.
6. **`/start` flow** (`handlers/common.py`):

   | Who | Reply |
   |---|---|
   | Admin or active user with a permission | Greeting + main menu |
   | Unknown user | Create `pending` user; "Запрос отправлен администратору"; send the admin a request card |
   | Pending | "Ваш запрос на рассмотрении" |
   | Blocked, or active without permissions | "Доступ закрыт" |

7. **Access request card** (`handlers/users.py`): to the admin: name, `@username`, Telegram ID, and inline buttons **Загрузка / Отчёты / Оба / Отклонить**. On click: update the user, edit the card to show the result, notify the user (with the main menu if approved).
8. **`/users` and "Пользователи"** (admin only): list users grouped by status as inline buttons → user card with toggles **Загрузка ✓/✗**, **Отчёты ✓/✗**, **Заблокировать / Разблокировать**, **Назад**. The admin cannot change themself.
9. **`/menu`**: show the main menu. **`/cancel` and "Отмена"**: clear any FSM state and show the main menu.
10. **Fallback router** (last in `ROUTERS`):
    - Not allowed users: "Доступ закрыт" (or the pending text).
    - Allowed users pressing a menu button with no handler yet: "Функция в разработке".
    - Anything else: "Не понял. Используйте меню."
11. **Commands**: `set_my_commands` with the full command list from architecture section 9 (Russian descriptions), so later phases don't need to touch it.

## Out of scope

Features behind the menu buttons (phases 03–06). Audit log.

## Done when

- [ ] A new Telegram account sends `/start` → gets "request sent"; the admin gets the card.
- [ ] Admin taps **Оба** → the user is notified and sees Upload + View buttons; taps **Отчёты** for another user → only View buttons.
- [ ] **Отклонить** → user gets "Доступ закрыт"; their messages get the same reply.
- [ ] `/users` toggles change the user's menu after they send `/menu`.
- [ ] A View-only user cannot use `/users` or Upload buttons.
- [ ] `/cancel` works from any state; unknown text gets the fallback reply.

## Handoff

Update the Status column and add a handoff note in [AGENTS.md](../../AGENTS.md).
