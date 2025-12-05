import os
import datetime
import glob
import requests
import threading
import concurrent.futures
import paramiko
import time
from git import Repo, InvalidGitRepositoryError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
ROUTER_HOSTS = os.getenv("ROUTER_HOSTS", "").split(",")
PORT = os.getenv("PORT", "22")
USERNAME = os.getenv("DATACOM_USERNAME")
PASSWORD = os.getenv("DATACOM_PASSWORD")
BACKUP_DIR = os.getenv("BACKUP_DIR", "/backups")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Lock for Git operations to prevent race conditions
GIT_LOCK = threading.Lock()

def get_timestamp():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def send_telegram_notification(message):
    """Sends a notification to Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials not configured. Skipping notification.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("Telegram notification sent.")
    except Exception as e:
        print(f"Failed to send Telegram notification: {e}")

def init_git_repo():
    """Initializes a git repository in the backup directory if it doesn't exist."""
    try:
        repo = Repo(BACKUP_DIR)
    except InvalidGitRepositoryError:
        print("Initializing Git repository...")
        repo = Repo.init(BACKUP_DIR)
    return repo

MAX_BACKUPS = int(os.getenv("MAX_BACKUPS", "10"))

def commit_to_git(repo, filename, hostname):
    """Commits the change to git."""
    try:
        # Path relativo incluindo a pasta do hostname
        relative_path = os.path.join(hostname, filename)
        repo.index.add([relative_path])
        # Always commit since filename is unique
        repo.index.commit(f"Backup {hostname} - {filename}")
        print(f"Committed {relative_path} to Git.")
    except Exception as e:
        print(f"Git commit failed: {e}")

def cleanup_old_backups(hostname):
    """Keeps only the last N backups for a given hostname."""
    try:
        # Buscar backups na pasta do hostname
        hostname_dir = os.path.join(BACKUP_DIR, hostname)
        if not os.path.exists(hostname_dir):
            return
        
        # Find all backups for this hostname dentro da pasta
        pattern = os.path.join(hostname_dir, f"{hostname}_*.conf")
        files = glob.glob(pattern)
        
        # Sort by modification time (newest last)
        files.sort(key=os.path.getmtime)
        
        if len(files) > MAX_BACKUPS:
            files_to_delete = files[:-MAX_BACKUPS]
            for f in files_to_delete:
                os.remove(f)
                print(f"Deleted old backup: {f}")
                
                # Optional: Remove from git index if you want to keep git clean, 
                # but usually we keep history in git and only clean disk.
                # If we want to remove from git as well:
                # repo.index.remove([f]) 
    except Exception as e:
        print(f"Cleanup failed for {hostname}: {e}")

def backup_router(hostname, repo):
    print(f"Starting backup for {hostname}...")
    start_time = datetime.datetime.now()
    
    # Criar cliente SSH Paramiko
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # Conectar ao dispositivo
        print(f"Connecting to {hostname}...")
        client.connect(
            hostname=hostname.strip(),
            username=USERNAME,
            password=PASSWORD,
            port=int(PORT),
            timeout=30,
            look_for_keys=False,
            allow_agent=False,
            banner_timeout=30
        )
        
        print(f"Connected to {hostname}")
        
        # Usar exec_command para executar comandos de forma não-interativa
        # Isso evita problemas com paginação e prompts
        
        # Obter configuração completa
        stdin, stdout, stderr = client.exec_command("show running-config", timeout=60)
        config_output = stdout.read().decode('utf-8', errors='ignore')
        error_output = stderr.read().decode('utf-8', errors='ignore')
        
        if error_output:
            print(f"Warning: stderr output: {error_output}")
        
        # Extrair hostname da configuração
        device_hostname = hostname.strip()  # Default para o IP
        for line in config_output.split('\n'):
            if 'hostname' in line.lower() and not line.strip().startswith('!') and not line.strip().startswith('#'):
                parts = line.split()
                if len(parts) >= 2 and parts[0].lower() == 'hostname':
                    device_hostname = parts[1]
                    break
        
        # Sanitizar hostname para uso em nome de arquivo
        device_hostname = device_hostname.replace(";", "").replace("/", "_").replace("\\", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace('"', "_").replace("<", "_").replace(">", "_").replace("|", "_")
        
        print(f"Device hostname: {device_hostname}")
        
        # Criar diretório para o hostname se não existir
        hostname_dir = os.path.join(BACKUP_DIR, device_hostname)
        os.makedirs(hostname_dir, exist_ok=True)
        
        # Salvar backup com timestamp dentro da pasta do hostname
        timestamp = get_timestamp()
        filename = f"{device_hostname}_{timestamp}.conf"
        filepath = os.path.join(hostname_dir, filename)
        
        with open(filepath, "w") as f:
            f.write(config_output)
        
        # Obter tamanho do arquivo
        file_size = os.path.getsize(filepath)
        file_size_kb = file_size / 1024
        
        # Calcular duração
        end_time = datetime.datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"Backup saved to {filepath}")
        
        # Seção crítica: operações Git e cleanup devem ser sequenciais
        with GIT_LOCK:
            # Commit no Git
            commit_to_git(repo, filename, device_hostname)
            
            # Cleanup de backups antigos
            cleanup_old_backups(device_hostname)
        
        # Retornar sucesso com detalhes
        return True, {
            "hostname": device_hostname,
            "ip": hostname.strip(),
            "filename": filename,
            "size_kb": file_size_kb,
            "duration": duration,
            "timestamp": timestamp
        }
        
    except paramiko.AuthenticationException as e:
        error_msg = f"Authentication failed for {hostname}: {e}"
        print(error_msg)
        return False, error_msg
    except paramiko.SSHException as e:
        error_msg = f"SSH error connecting to {hostname}: {e}"
        print(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"An error occurred with {hostname}: {e}"
        print(error_msg)
        return False, error_msg
    finally:
        try:
            client.close()
        except:
            pass

def main():
    if not ROUTER_HOSTS or ROUTER_HOSTS == ['']:
        print("No routers configured in ROUTER_HOSTS.")
        return

    if not USERNAME or not PASSWORD:
        print("Credentials not found in environment variables.")
        return

    # Ensure backup directory exists
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # Initialize Git
    repo = init_git_repo()

    print(f"Starting backup job for {len(ROUTER_HOSTS)} routers.")
    job_start_time = datetime.datetime.now()
    
    success_details = []
    failed_hosts = []

    # Use ThreadPoolExecutor for parallel backups
    # Default to 5 workers or the number of hosts, whichever is smaller
    max_workers = min(len(ROUTER_HOSTS), 10)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Create a dictionary to map futures to hosts
        future_to_host = {executor.submit(backup_router, host, repo): host for host in ROUTER_HOSTS if host}
        
        for future in concurrent.futures.as_completed(future_to_host):
            host = future_to_host[future]
            try:
                success, result = future.result()
                if success:
                    success_details.append(result)
                else:
                    failed_hosts.append({"ip": host.strip(), "error": result})
            except Exception as exc:
                failed_hosts.append({"ip": host.strip(), "error": f"Thread exception: {exc}"})

    job_end_time = datetime.datetime.now()
    total_duration = (job_end_time - job_start_time).total_seconds()

    # Send Telegram Notification
    if failed_hosts or success_details:
        # Build enhanced message
        message_lines = []
        
        if failed_hosts:
            message_lines.append("🔴 *BACKUP JOB - FALHA PARCIAL*")
        else:
            message_lines.append("✅ *BACKUP JOB - SUCESSO*")
        
        message_lines.append("━━━━━━━━━━━━━━━━━━━━")
        
        # Job summary
        message_lines.append(f"📊 *Resumo da Execução*")
        message_lines.append(f"• Total de dispositivos: `{len(ROUTER_HOSTS)}`")
        message_lines.append(f"• Sucesso: `{len(success_details)}`")
        message_lines.append(f"• Falhas: `{len(failed_hosts)}`")
        message_lines.append(f"• Duração total: `{total_duration:.2f}s`")
        message_lines.append(f"• Horário: `{job_end_time.strftime('%d/%m/%Y %H:%M:%S')}`")
        message_lines.append("")
        
        # Success details
        if success_details:
            message_lines.append("✅ *Backups Realizados*")
            message_lines.append("━━━━━━━━━━━━━━━━━━━━")
            for detail in success_details:
                message_lines.append(f"🖥 *{detail['hostname']}*")
                message_lines.append(f"  • Arquivo: `{detail['filename']}`")
                message_lines.append(f"  • Tamanho: `{detail['size_kb']:.2f} KB`")
                message_lines.append(f"  • Tempo: `{detail['duration']:.2f}s`")
                message_lines.append("")
        
        # Failed details
        if failed_hosts:
            message_lines.append("❌ *Falhas*")
            message_lines.append("━━━━━━━━━━━━━━━━━━━━")
            for failed in failed_hosts:
                message_lines.append(f"🖥 IP: `{failed['ip']}`")
                message_lines.append(f"  • Erro: `{failed['error']}`")
                message_lines.append("")
        
        message = "\n".join(message_lines)
        send_telegram_notification(message)

    print("Backup job completed.")

if __name__ == "__main__":
    main()
