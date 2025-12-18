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
