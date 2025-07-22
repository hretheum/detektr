# Przewodnik rozszerzenia przestrzeni dyskowej na Nebuli

## Problem
- Partycja systemowa: tylko 39GB wolnego miejsca (59% zajęte)
- Docker używa 33GB+ (obrazy + cache)
- Redis persistence, logi i dane będą rosły

## Dostępne zasoby
- **Dysk 1 (nvme0n1)**: 1.82TB całkowicie
  - Używane: 100GB (LVM logical volume)
  - **WOLNE**: 1.72TB w volume group
- **Dysk 2 (nvme1n1)**: 931GB (partycje NTFS - prawdopodobnie Windows)

## Rekomendowane rozwiązania

### Opcja 1: Rozszerzenie partycji systemowej (REKOMENDOWANE) ⭐

Najprostsze i najbezpieczniejsze rozwiązanie - rozszerzyć istniejącą partycję.

```bash
# 1. Sprawdź obecny stan
sudo lvs
sudo vgs

# 2. Rozszerz logical volume o 200GB
sudo lvextend -L +200G /dev/ubuntu-vg/ubuntu-lv

# 3. Rozszerz filesystem
sudo resize2fs /dev/ubuntu-vg/ubuntu-lv

# 4. Weryfikuj
df -h /
```

**Zalety**:
- Bez przerwy w działaniu
- Natychmiastowy efekt
- Brak zmian w konfiguracji

### Opcja 2: Dedykowana partycja dla Docker

Utworzenie osobnej partycji LVM dla Docker.

```bash
# 1. Utwórz nowy logical volume 500GB
sudo lvcreate -L 500G -n docker-lv ubuntu-vg

# 2. Sformatuj jako ext4
sudo mkfs.ext4 /dev/ubuntu-vg/docker-lv

# 3. Zatrzymaj Docker
sudo systemctl stop docker

# 4. Przenieś dane Docker
sudo mkdir /mnt/docker-new
sudo mount /dev/ubuntu-vg/docker-lv /mnt/docker-new
sudo rsync -av /var/lib/docker/ /mnt/docker-new/

# 5. Podmień mount point
sudo umount /mnt/docker-new
sudo mv /var/lib/docker /var/lib/docker.old
sudo mkdir /var/lib/docker
sudo mount /dev/ubuntu-vg/docker-lv /var/lib/docker

# 6. Dodaj do /etc/fstab
echo "/dev/ubuntu-vg/docker-lv /var/lib/docker ext4 defaults 0 2" | sudo tee -a /etc/fstab

# 7. Uruchom Docker
sudo systemctl start docker

# 8. Po weryfikacji usuń stare dane
sudo rm -rf /var/lib/docker.old
```

**Zalety**:
- Separacja danych Docker
- Łatwe zarządzanie przestrzenią
- Możliwość snapshots

### Opcja 3: Dedykowane volumes dla persistence

Utworzenie osobnych LVM volumes dla danych aplikacji.

```bash
# 1. Volume dla Redis persistence
sudo lvcreate -L 50G -n redis-data-lv ubuntu-vg
sudo mkfs.ext4 /dev/ubuntu-vg/redis-data-lv
sudo mkdir -p /data/redis
sudo mount /dev/ubuntu-vg/redis-data-lv /data/redis

# 2. Volume dla PostgreSQL
sudo lvcreate -L 100G -n postgres-data-lv ubuntu-vg
sudo mkfs.ext4 /dev/ubuntu-vg/postgres-data-lv
sudo mkdir -p /data/postgres
sudo mount /dev/ubuntu-vg/postgres-data-lv /data/postgres

# 3. Dodaj do /etc/fstab
cat << EOF | sudo tee -a /etc/fstab
/dev/ubuntu-vg/redis-data-lv /data/redis ext4 defaults 0 2
/dev/ubuntu-vg/postgres-data-lv /data/postgres ext4 defaults 0 2
EOF

# 4. Zaktualizuj docker-compose.yml
# Zmień volumes na:
# redis:
#   volumes:
#     - /data/redis:/data
# postgres:
#   volumes:
#     - /data/postgres:/var/lib/postgresql/data
```

**Zalety**:
- Najlepsza kontrola
- Osobne limity dla każdej usługi
- Łatwe backupy

## Natychmiastowe działania

Zanim zdecydujesz o długoterminowym rozwiązaniu:

### 1. Wyczyść cache Docker
```bash
# Usuń nieużywane obrazy, kontenery i cache
docker system prune -a --volumes
# To może zwolnić 15-20GB!
```

### 2. Ogranicz logi
```bash
# Dodaj do docker-compose.yml dla każdego serwisu:
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### 3. Konfiguruj Redis z limitem pamięci
```bash
# W docker-compose.yml dla Redis:
command: redis-server --maxmemory 4gb --maxmemory-policy allkeys-lru
```

## Rekomendacja

**Dla szybkiego rozwiązania**: Opcja 1 - rozszerz partycję systemową o 200-300GB.

**Dla długoterminowej skalowalności**: Kombinacja Opcji 1 i 3:
1. Rozszerz system o 100GB (dla Docker images i logów)
2. Utwórz dedykowane volumes dla danych (Redis, PostgreSQL, etc.)

## Monitoring przestrzeni

Dodaj alerty gdy przestrzeń < 20%:
```bash
# Prosty skrypt monitoringu
cat > /opt/detektor/scripts/disk-monitor.sh << 'EOF'
#!/bin/bash
THRESHOLD=80
USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $USAGE -gt $THRESHOLD ]; then
    echo "ALERT: Disk usage is ${USAGE}% on $(hostname)"
    # Dodaj powiadomienie (email, Slack, etc.)
fi
EOF

# Dodaj do crontab
echo "0 * * * * /opt/detektor/scripts/disk-monitor.sh" | crontab -
```
