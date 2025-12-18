# Internal IT Wiki (FastAPI)

Минимальная внутренняя wiki-система без базы данных. Контент хранится на файловой системе в `/opt/wiki/content`.

## Быстрый старт (Debian 12, root)

```bash
apt update
apt install -y python3-venv python3-pip

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

uvicorn app.main:app --host 0.0.0.0 --port 8080
```

### Основные возможности
- Хранение на ФС `/opt/wiki/content`, без БД, защита от path traversal.
- CRUD по API: создание папок/страниц, сохранение Markdown, загрузка вложений (в `assets/`), мягкое удаление в `.trash/<timestamp>/...`.
- Обновление индекса поиска (заголовок meta.json + содержимое markdown) при любых изменениях.
- VMware-like тёмный UI с деревом слева, хлебными крошками, вкладками сервисов, превью Markdown, mermaid и подсветкой кода.
- Демоданные создаются при первом запуске (Company_A/B + DC + сервисы).

### API (основные)
- `POST /api/mkdir` — `{parent, name, title, type_value}` создать папку + meta.json.
- `POST /api/create-page` — `{parent, name, title, type_value}` для document/service/server/network с шаблонными `.md`.
- `POST /api/save` — `{path, file_name, content}` сохранить markdown и обновить `meta.json.updated`.
- `POST /api/upload` — `Form(path, file)` загрузить в `assets/`.
- `POST /api/trash` — `{path}` переместить в `.trash/<timestamp>/<path>`.
- Контракт ответа создания: `{ "ok": true, "path": "<relative>", "view_url": "/view/<relative>" }`.

### Быстрая самопроверка
1. Создать компанию: отправить `POST /api/mkdir` с `{"parent":"","name":"FD","title":"FD","type_value":"company"}`.
2. Убедиться, что появилась папка: `/opt/wiki/content/FD`.
3. Открыть в браузере `/view/FD` — должна открыться HTML-страница wiki (без JSON 404).

### Правила System Name
- Допустимы только латиница, цифры, символы `-` и `_`.
- Пробелы заменяются на `-`, кириллица требует ручного/авто-транслита.
- При ошибке валидации API вернёт `{ "ok": false, "error": "...", "field": "name" }` с кодом 400/409.

### Структура
- В корне — только Company.
- Внутри Company — только DC.
- Внутри DC или Section — Section/Document/Service/Server/Network.
- Каждый узел: папка + `meta.json` + `index.md` (Service дополнительно вкладки `overview.md` ... `service-network.md`).

### Тест-кейс
1. Создать Company «Первый Дом» через `/api/mkdir` (`parent=""`, `type="company"`).
2. Внутри неё создать DC «Машкова» (`parent="Pervyy_Dom"` после slug).
3. Внутри DC создать Document «Первая приемная`.
4. Проверить: DC отображается внутри компании в дереве; `/view/<company>/<dc>` показывает страницу; `/view/<company>/<dc>/<doc>` открывает `index.md`.

### Дополнительно: systemd unit (опционально)

Создайте файл `/etc/systemd/system/internal-wiki.service`:

```ini
[Unit]
Description=Internal Wiki
After=network.target

[Service]
Type=simple
WorkingDirectory=/workspace/Wiki6
ExecStart=/workspace/Wiki6/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now internal-wiki.service
```
