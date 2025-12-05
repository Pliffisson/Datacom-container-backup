# 🛡️ Datacom Backup Automation

![Python](https://img.shields.io/badge/Python-3.9-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Paramiko](https://img.shields.io/badge/Paramiko-3.4.0-orange?style=for-the-badge)
![Datacom](https://img.shields.io/badge/Datacom-DmOS-00A0E3?style=for-the-badge&logo=cisco&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active-success?style=for-the-badge)

Sistema automatizado para backup de configurações de equipamentos **Datacom DmOS** via SSH, com versionamento Git e notificações Telegram.

---

## 🎯 O que faz?

- 🔄 **Backup automático** de configurações via SSH
- 📁 **Organiza** backups em pastas por equipamento
- 🕐 **Agenda** execução diária via Cron
- 📝 **Versiona** mudanças com Git
- 📱 **Notifica** resultados via Telegram
- 🧹 **Limpa** backups antigos automaticamente

---

## 🚀 Início Rápido

### 1️⃣ Configure as credenciais

Copie o arquivo de exemplo e edite com seus dados:

```bash
cp .env.example .env
nano .env
```

**Configurações principais:**

```ini
# IPs dos equipamentos (separados por vírgula)
ROUTER_HOSTS=192.168.1.1,192.168.1.2,192.168.1.3

# Credenciais SSH
DATACOM_USERNAME=admin
DATACOM_PASSWORD=sua_senha

# Quantos backups manter por equipamento
MAX_BACKUPS=10

# Telegram (opcional)
TELEGRAM_BOT_TOKEN=seu_token
TELEGRAM_CHAT_ID=seu_chat_id
```

### 2️⃣ Inicie o container

```bash
docker compose up --build -d
```

Pronto! O backup será executado automaticamente todo dia às **22:00**.

### 3️⃣ Teste manualmente (opcional)

Para executar um backup agora:

```bash
docker exec datacom-backup python3 src/backup.py
```

---

## 📂 Onde ficam os backups?

Os backups são salvos em `backups/` organizados por equipamento:

```
backups/
├── SW02-PC01/
│   ├── SW02-PC01_20251205_132119.conf
│   └── SW02-PC01_20251204_220000.conf
├── SW02-PC05/
│   ├── SW02-PC05_20251205_132107.conf
│   └── SW02-PC05_20251204_220000.conf
└── ...
```

**Formato do arquivo:** `HOSTNAME_AAAAMMDD_HHMMSS.conf`

---

## ⚙️ Configurações Avançadas

### Alterar horário do backup

Edite o arquivo `crontab`:

```bash
# Padrão: todo dia às 22:00
0 22 * * *

# Exemplos:
0 3 * * *     # Todo dia às 03:00
0 */6 * * *   # A cada 6 horas
0 0 * * 0     # Todo domingo à meia-noite
```

Após alterar, reconstrua o container:

```bash
docker compose up --build -d
```

### Ver logs

```bash
docker compose logs -f
```

### Ver histórico Git

```bash
cd backups/
git log --oneline
```

---

## 📱 Notificações Telegram

As notificações incluem:

- ✅ Status (sucesso/falha)
- 📊 Resumo (total, sucessos, falhas)
- 🖥️ Nome de cada equipamento
- 📄 Arquivo gerado
- 💾 Tamanho do backup
- ⏱️ Tempo de execução
- 🕐 Horário

### Como configurar

1. Crie um bot no Telegram com [@BotFather](https://t.me/botfather)
2. Copie o **token** do bot
3. Obtenha seu **chat_id** enviando `/start` para [@userinfobot](https://t.me/userinfobot)
4. Adicione no `.env`:

```ini
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

---

## 🔧 Como Funciona

### Tecnologia

- **Paramiko**: Conexão SSH direta e confiável
- **Docker**: Isolamento e portabilidade
- **Git**: Versionamento automático
- **Cron**: Agendamento de tarefas

### Fluxo do Backup

1. 🔌 Conecta via SSH no equipamento
2. 📥 Executa `show running-config`
3. 🏷️ Detecta o hostname automaticamente
4. 📁 Cria pasta para o equipamento (se não existir)
5. 💾 Salva arquivo com timestamp
6. 📝 Faz commit no Git
7. 🧹 Remove backups antigos (mantém últimos N)
8. 📱 Envia notificação Telegram

### Por que Paramiko?

✅ Não depende de detecção de prompt  
✅ Captura configuração completa sem paginação  
✅ Mais confiável para equipamentos Datacom  
✅ Execução não-interativa (mais rápido)

---

## ❓ Problemas Comuns

### Backup não executa

```bash
# Verifique se o container está rodando
docker ps

# Veja os logs
docker compose logs -f
```

### Erro de autenticação

- Verifique usuário e senha no `.env`
- Confirme que o usuário tem permissão SSH no equipamento

### Backup incompleto

- O script usa `exec_command` que captura tudo de uma vez
- Não há problemas de paginação (`--More--`)

---

## 📦 Dependências

- **paramiko==3.4.0** - Biblioteca SSH
- **GitPython==3.1.40** - Integração Git
- **python-dotenv==1.0.0** - Variáveis de ambiente
- **requests==2.31.0** - Notificações Telegram

---

## 📄 Licença

Este projeto é de código aberto. Use livremente! 🎉
