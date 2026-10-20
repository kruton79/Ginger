# Трекер тренувань

Вебсервіс (Flask + SQLite) для відстеження прогресу в тренуваннях: планові та фактичні підходи, повтори, нотатки.

## Опис теми
Назва:        Трекер тренувань
Для кого:     для мене, щоб бачити прогрес в тренуваннях
Запис:        дата; вправа; план_підходів; факт_підходів; повтори; нотатка
Операції:     додати, показати всі, знайти за вправою, видалити
Звіти:        загальна кількість запланованих і виконаних підходів та повторень за кожною вправою

## Запуск
```
python -m venv venv
venv\Scripts\activate          # Windows;  Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
python app.py
```
Сервер: http://127.0.0.1:5000. Режим розробки з автоперезапуском: `FLASK_DEBUG=1 python app.py`
(PowerShell: `$env:FLASK_DEBUG=1; python app.py`). На сервері debug вмикати не можна.

Тести (сервер для них запускати не треба):
```
python tests.py
python tests_api.py
```

## Перевірка через curl (в іншому вікні терміналу)
У Windows PowerShell пишіть `curl.exe`, а не `curl`, а JSON краще класти у файл (`-d "@item.json"`), щоб лапки не ламалися.

1. Додати запис:
```
curl -X POST http://127.0.0.1:5000/items -H "Content-Type: application/json" -d '{"date": "2026-10-10", "exercise": "Відтискання", "target_sets": 4, "sets": 4, "reps": 20, "note": "Клас"}'
```
2. Отримати всі записи:
```
curl http://127.0.0.1:5000/items
```
3. Знайти за вправою (регістр не важливий). Кирилицю в URL кодуємо через `-G --data-urlencode`:
```
curl -G http://127.0.0.1:5000/items --data-urlencode "exercise=Відтискання"
```
4. Звіт:
```
curl http://127.0.0.1:5000/report
```
5. Видалити запис за ID (наприклад, ID = 1):
```
curl -X DELETE http://127.0.0.1:5000/items/1
```

## Помилки
Усі помилки приходять як JSON `{"error": "..."}`, ніколи як HTML і ніколи з деталями внутрішнього устрою.

| Код | Коли |
| --- | --- |
| 400 | не JSON, немає обов'язкових полів, неправильний тип/діапазон/довжина, неіснуюча дата, порожній `?exercise=`, `ID` не є додатним цілим |
| 404 | запису з таким ID немає, або такого маршруту немає |
| 405 | неправильний HTTP-метод для маршруту |
| 413 | запит більший за 10 КБ |
| 500 | непередбачена помилка сервера (подробиці лише в логу) |
| 503 | база даних тимчасово недоступна |

Обмеження: `date` формату РРРР-ММ-ДД (існуюча дата); `target_sets`, `sets`, `reps` цілі від 0 до 10000;
`exercise` до 100 символів, `note` до 500.

Перевірка помилок:
```
curl -i -X POST http://127.0.0.1:5000/items -H "Content-Type: application/json" -d '{"exercise": "x"}'
curl -i -X DELETE http://127.0.0.1:5000/items/99999
curl -i -X DELETE http://127.0.0.1:5000/items/abc
```

## Формат даних
База `data.db` (SQLite, створюється поруч з кодом автоматично), таблиця `items`:
`id, date, exercise, target_sets, sets, reps, note`


## Розгортання

Сервіс працює на віртуальній машині Google Cloud (e2-micro, Ubuntu 24.04, регіон us-central1) за адресою https://api.shylko.pp.ua/items. Ланцюжок: nginx (80/443, HTTPS) → gunicorn (127.0.0.1:8000) → Flask.

1. Домен shylko.pp.ua зареєстровано на nic.ua, активовано через Telegram-бота @ppuabot. У DNS додано записи A: `api` і `@` на статичну IP-адресу сервера.
2. Створено віртуальну машину з дозволеним HTTP/HTTPS трафіком, зарезервовано статичну зовнішню IP-адресу.
3. Згенеровано ключ (`ssh-keygen -t ed25519`), публічну частину додано в Compute Engine → Metadata → SSH keys у форматі `artem:ssh-ed25519 AAAA...`. Вхід: `ssh artem@ВАШ_IP`.
4. Встановлення пакетів і фаєрвол:
```
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3-venv python3-pip nginx ufw sqlite3
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```
5. Вхід за паролем і під root вимкнено: у `/etc/ssh/sshd_config` задано `PasswordAuthentication no` і `PermitRootLogin no`, потім `sudo systemctl restart ssh`.
6. Код і залежності (gunicorn уже є в requirements.txt, тому `pip freeze` на сервері не потрібен і файл у репозиторії лишається незмінним):
```
cd ~
git clone https://github.com/kruton79/Ginger.git
cd Ginger
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
7. Перевірка gunicorn: `gunicorn -w 2 -b 127.0.0.1:8000 app:app`, у другому вікні `curl http://127.0.0.1:8000/items`.
8. Автозапуск через systemd (файл `deploy/ginger.service`):
```
sudo cp deploy/ginger.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ginger
sudo systemctl status ginger
```
9. nginx (файл `deploy/nginx.conf`):
```
sudo cp deploy/nginx.conf /etc/nginx/sites-available/ginger
sudo ln -s /etc/nginx/sites-available/ginger /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```
10. HTTPS через Let's Encrypt:
```
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/local/bin/certbot
sudo certbot --nginx -d api.shylko.pp.ua
sudo certbot renew --dry-run
```
11. Оновлення коду: `cd ~/Ginger && git pull && sudo systemctl restart ginger`. Логи: `sudo journalctl -u ginger -n 50`.
