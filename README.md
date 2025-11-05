# Sinum Home Assistant Integration

Integrácia pre Home Assistant na pripojenie k lokálnemu Sinum systému a čítanie teplôt z jednotlivých miestností.

## Inštalácia

### Cez HACS (odporúčané)

HACS automaticky stiahne a nainštaluje integráciu z GitHub repository.

**Postup:**

1. Otvorte HACS v Home Assistant
2. Prejdite na "Integrácie"
3. Kliknite na tri bodky v pravom hornom rohu → "Custom repositories"
4. Pridajte tento repozitár:
   - **URL**: `https://github.com/dbaranec/sinum` (alebo URL vášho repository)
   - **Kategória**: **Integration**
   - Kliknite na **ADD**
5. Po pridaní sa "Sinum" zobrazí v zozname integrácií
6. Kliknite na "Sinum" → **Download**
7. Reštartujte Home Assistant

**Ako to funguje:**
- HACS načíta repository z GitHub URL
- Hľadá integráciu v priečinku `custom_components/sinum/`
- Kontroluje `manifest.json` a `hacs.json` pre metadata
- Stiahne súbory do `custom_components/sinum/` vo vašom Home Assistant
- Home Assistant automaticky rozpozná novú integráciu

**Dôležité pre HACS:**
- Repository musí byť verejný na GitHub (alebo použiť private repository s tokenom)
- Štruktúra musí byť: `custom_components/sinum/` v root adresári repository
- Musí obsahovať `manifest.json` s `domain: "sinum"`
- Voliteľne `hacs.json` pre dodatočné informácie

**Odkaz na dokumentáciu HACS:** [Custom Repositories](https://www.hacs.xyz/docs/faq/custom_repositories/)

### Lokálna inštalácia (pre testovanie bez GitHubu)

Ak chcete testovať integráciu lokálne bez toho, aby ste ju museli najprv nahrať na GitHub:

**Postup:**

1. **Nájdite adresár Home Assistant:**
   - Pre Home Assistant OS na sieti: `/config/` (prístupné cez SSH alebo Samba)
   - Pre Docker: `/config/` (zvyčajne mapovaný na `~/homeassistant/`)
   - Pre venv/venv: `~/.homeassistant/` alebo cestu kde beží HA

2. **Skopírujte integráciu:**

   **A) Cez SSH (ak máte Home Assistant na sieti, napr. 192.168.1.50):**
   ```bash
   # Automatický skript (upravte HA_IP v install_local.sh):
   ./install_local.sh
   
   # Alebo manuálne cez SSH:
   scp -r /Users/dbaranec/Workspace/sinum/custom_components/sinum root@192.168.1.50:/config/custom_components/
   
   # Reštartujte HA:
   ssh root@192.168.1.50 "ha core restart"
   ```
   
   **B) Cez Samba share (ak je povolený):**
   ```bash
   # Pripojte sa na Samba share:
   # Connect to: smb://192.168.1.50/config
   # Potom skopírujte priečinok sinum do custom_components/
   ```
   
   **C) Lokálne kopírovanie (ak máte mountovaný config adresár):**
   ```bash
   cp -r /Users/dbaranec/Workspace/sinum/custom_components/sinum /config/custom_components/
   ```
   
   **D) Symlink pre development (zmeny sa prejavia automaticky po reštarte):**
   ```bash
   # Lokálne:
   ln -s /Users/dbaranec/Workspace/sinum/custom_components/sinum /config/custom_components/sinum
   
   # Cez SSH (nepraktické, lepšie kopírovať):
   # ssh root@192.168.1.50 "ln -s /mnt/sdb1/sinum /config/custom_components/sinum"
   ```

3. **Skontrolujte štruktúru:**
   ```
   /config/
   ├── configuration.yaml
   └── custom_components/
       └── sinum/
           ├── __init__.py
           ├── manifest.json
           ├── config_flow.py
           └── ...
   ```

3. **Reštartujte Home Assistant:**
   - Pre Home Assistant OS na sieti: `ssh root@192.168.1.50 "ha core restart"` alebo cez UI
   - Pre Docker: `docker restart homeassistant`
   - Pre venv: Reštartujte službu

4. **Skontrolujte logy:**
   ```bash
   # Cez SSH:
   ssh root@192.168.1.50 "ha core logs | grep sinum"
   
   # Alebo cez UI: Developer Tools → Logs
   # V logoch by ste mali vidieť: "Loading integration: sinum"
   ```

**Výhody lokálneho testovania:**
- ✅ Okamžité zmeny bez pushovania na GitHub
- ✅ Rýchlejší development cyklus
- ✅ Jednoduchšie debugovanie
- ✅ Môžete použiť symlink pre automatické aktualizácie

**Symlink vs. kopírovanie:**
- **Symlink**: Zmeny v projekte sa okamžite prejavia (potrebuje reštart HA)
- **Kopírovanie**: Musíte kopírovať súbory zakaždým po zmene

**Tipy pre development:**
- Zapnite debug logy v `configuration.yaml`:
  ```yaml
  logger:
    default: info
    logs:
      custom_components.sinum: debug
  ```
- Skontrolujte logy: `tail -f /config/home-assistant.log | grep sinum`

## Konfigurácia

1. Prejdite do **Nastavenia** → **Zariadenia a služby**
2. Kliknite na **Pridať integráciu**
3. Vyhľadajte **Sinum**
4. Zadajte:
   - **Host**: IP adresa alebo hostname vášho Sinum systému (napr. `http://192.168.1.100:8080` alebo `http://sinum.local:8080`)
   - **Username**: Používateľské meno
   - **Password**: Heslo
5. Kliknite na **Odoslať**

## Konfigurácia API

**Dôležité**: Táto integrácia obsahuje základnú implementáciu API klienta. Je potrebné upraviť súbor `custom_components/sinum/api.py` podľa skutočného API vášho Sinum systému.

### Čo je potrebné upraviť v `api.py`:

1. **Autentifikácia** (`async_authenticate`):
   - URL endpoint pre prihlásenie
   - Formát požiadavky (JSON, form-data, atď.)
   - Spôsob získania autentifikačného tokenu

2. **Získanie miestností** (`async_get_rooms`):
   - URL endpoint pre získanie zoznamu miestností
   - Formát odpovede API
   - Očakávaný formát dát: `[{"id": 1, "name": "Obývačka", "temperature": 22.5}, ...]`

### Príklad úpravy pre konkrétne API:

```python
# Ak máte API endpoint /api/v1/login
auth_url = f"{self.host}/api/v1/login"

# Ak váš API používa iný formát autentifikácie
async with session.post(
    auth_url,
    auth=aiohttp.BasicAuth(self.username, self.password),
    timeout=aiohttp.ClientTimeout(total=10),
) as response:
    # ...
```

## Senzory

Po úspešnej konfigurácii sa vytvoria teplotné senzory pre každú miestnosť:
- `sensor.sinum_[nazov_miestnosti]` - teplota v miestnosti

## Podpora

Ak narazíte na problémy, skontrolujte:
1. Logy Home Assistant na chybové hlásenia
2. Správnosť prihlasovacích údajov
3. Dostupnosť Sinum API na zadanej adrese
4. Kompatibilitu API formátu (možno je potrebné upraviť `api.py`)

