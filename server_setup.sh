#!/bin/bash

# Создание нового пользователя
adduser --disabled-password --gecos "" botgrover
usermod -aG sudo botgrover

# Создание директории .ssh
mkdir -p /home/botgrover/.ssh
chmod 700 /home/botgrover/.ssh

# Генерация SSH ключа для GitHub Actions
ssh-keygen -t ed25519 -f /home/botgrover/.ssh/github_actions -N ""

# Добавление публичного ключа в authorized_keys
cat /home/botgrover/.ssh/github_actions.pub >> /home/botgrover/.ssh/authorized_keys
chmod 600 /home/botgrover/.ssh/authorized_keys

# Установка правильных прав
chown -R botgrover:botgrover /home/botgrover/.ssh

# Настройка sudo без пароля для определенных команд
echo "botgrover ALL=(ALL) NOPASSWD: /bin/systemctl restart botgrover" >> /etc/sudoers.d/botgrover
chmod 440 /etc/sudoers.d/botgrover

# Установка необходимых пакетов
apt update
apt install -y python3-venv python3-pip git nginx

# Клонирование репозитория
su - botgrover -c "git clone https://github.com/your-username/BotGrover.git"
cd /home/botgrover/BotGrover

# Настройка виртуального окружения
su - botgrover -c "cd ~/BotGrover && python3 -m venv venv"
su - botgrover -c "cd ~/BotGrover && source venv/bin/activate && pip install -r requirements.txt"

# Создание systemd сервиса
cat > /etc/systemd/system/botgrover.service << EOL
[Unit]
Description=BotGrover Telegram Bot
After=network.target

[Service]
Type=simple
User=botgrover
WorkingDirectory=/home/botgrover/BotGrover
Environment=TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
ExecStart=/home/botgrover/BotGrover/venv/bin/python telegram_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOL

# Запуск сервиса
systemctl enable botgrover
systemctl start botgrover

# Вывод приватного ключа для GitHub Actions
echo "=== PRIVATE KEY FOR GITHUB ACTIONS ==="
cat /home/botgrover/.ssh/github_actions
echo "=== END PRIVATE KEY ===" 