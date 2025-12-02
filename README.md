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

## Konfigurácia

1. Prejdite do **Nastavenia** → **Zariadenia a služby**
2. Kliknite na **Pridať integráciu**
3. Vyhľadajte **Sinum**
4. Zadajte:
   - **Host**: Úplná URL adresa vášho Sinum systému
     - Príklady:
       - `https://sinum.local` (ak používate HTTPS na štandardnom porte 443) - **Odporúčané**
       - `https://sinum.local:443` (ekvivalent vyššie uvedeného)
       - `https://192.168.50.231` (ak používate IP adresu s HTTPS)
       - `http://sinum.local:8080` (iba ak API beží na HTTP porte 8080)
     - **Dôležité**: 
       - Ak port 443 funguje (HTTPS), použite `https://sinum.local` (port 443 je štandardný a nemusí byť v URL)
       - Port musí byť súčasťou URL len ak API nebeží na štandardnom porte (80 pre HTTP, 443 pre HTTPS)
   - **Username**: Používateľské meno
   - **Password**: Heslo
5. Kliknite na **Odoslať**

## API Implementácia

Integrácia je implementovaná podľa oficiálnej Sinum API dokumentácie: [apidocs.sinum.tech](https://apidocs.sinum.tech)

### API Endpointy:

1. **Autentifikácia**: `POST /api/v1/login`
   - Odošle `username` a `password` v JSON formáte
   - Vráti autentifikačný token

2. **Získanie miestností**: `GET /api/v1/rooms` (alebo podobný endpoint)
   - Vyžaduje Authorization header: `Bearer {token}`
   - Vráti zoznam miestností s teplotami

### Formát dát:

API očakáva tieto formáty odpovedí:

**Autentifikácia:**
```json
{
  "token": "your-auth-token-here"
}
```

**Miestnosti:**
```json
[
  {
    "id": 1,
    "name": "Obývačka",
    "temperature": 22.5
  },
  {
    "id": 2,
    "name": "Kuchyňa",
    "temperature": 21.0
  }
]
```

Alebo môže byť zabalené v objekte:
```json
{
  "rooms": [
    {"id": 1, "name": "Obývačka", "temperature": 22.5},
    {"id": 2, "name": "Kuchyňa", "temperature": 21.0}
  ]
}
```

## Senzory

Po úspešnej konfigurácii sa vytvoria nasledujúce senzory pre každú miestnosť:

### Teplotné senzory:
- `sensor.sinum_[nazov_miestnosti]` - teplota v miestnosti (°C)

### Vlhkostné senzory:
- `sensor.sinum_[nazov_miestnosti]_humidity` - vlhkosť v miestnosti (%)

### Binary senzory (stav okruhu):
- `binary_sensor.sinum_[nazov_miestnosti]_heating` - stav vykurovacieho okruhu (ON/OFF)
- `binary_sensor.sinum_[nazov_miestnosti]_cooling` - stav chladiacieho okruhu (ON/OFF)

**Poznámka**: Nie všetky senzory sa vytvoria pre každú miestnosť - závisí to od toho, aké zariadenia sú v danej miestnosti nainštalované.

## Riešenie problémov

### Ako zobraziť logy v Home Assistant

**Metóda 1: Cez Developer Tools (najjednoduchšie)**
1. Otvorte Home Assistant UI
2. V bočnom menu kliknite na **Developer Tools** (ikona kladiva)
3. Prejdite na záložku **Logs**
4. V poli "Filter" zadajte: `sinum` alebo `SinumAPI`
5. Zobrazia sa len relevantné logy

**Metóda 2: Cez Settings**
1. Otvorte **Settings** (Nastavenia)
2. Prejdite do **System**
3. Kliknite na **Logs**
4. V poli "Filter" zadajte: `sinum`

**Metóda 3: Zapnite debug logy pre detailnejšie informácie**

Pridajte do `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.sinum: debug
```

Po pridaní:
1. Reštartujte Home Assistant
2. Použite Metódu 1 alebo 2 na zobrazenie logov
3. Uvidíte detailné informácie o:
   - Autentifikácii
   - Obnovovaní tokenu
   - API požiadavkách
   - Chybách

**Čo hľadať v logoch:**
- `Successfully authenticated` - úspešné prihlásenie
- `Token expired, re-authenticating` - automatické obnovovanie tokenu
- `Retrieved X rooms with temperatures` - úspešné získanie dát
- Chybové správy začínajúce `ERROR` alebo `WARNING`

### Chyba "invalid_auth"

Ak dostávate chybu "invalid_auth" aj keď sú údaje správne:

1. **Zapnite debug logy** (pozri vyššie)
2. **Skontrolujte logy** v Home Assistant (pozri vyššie)
3. Hľadajte správy obsahujúce "sinum" alebo "SinumAPI"

3. **Overte API endpoint**:
   - Skontrolujte, či API je dostupné na vašej URL (napr. `https://sinum.local/api/v1/login`)
   - Môžete skúsiť otvoriť v prehliadači alebo pomocou curl:
     ```bash
     # Ak používate HTTPS (odporúčané):
     curl -X POST https://sinum.local/api/v1/login \
       -H "Content-Type: application/json" \
       -d '{"username":"Dominik","password":"your_password"}'
     
     # Alebo ak používate IP adresu:
     curl -X POST https://192.168.50.231/api/v1/login \
       -H "Content-Type: application/json" \
       -d '{"username":"Dominik","password":"your_password"}'
     
     # Poznámka: Ak máte SSL certifikát problémy, môžete skúsiť:
     curl -k -X POST https://sinum.local/api/v1/login \
       -H "Content-Type: application/json" \
       -d '{"username":"Dominik","password":"your_password"}'
     ```
   
   **Poznámka**: Port 443 je štandardný HTTPS port a nemusí byť v URL (`https://sinum.local` je ekvivalentné `https://sinum.local:443`)

4. **Možné príčiny**:
   - Nesprávny protokol (HTTP vs HTTPS) - skontrolujte pomocou `nc -zv IP_ADRESA PORT`
   - Nesprávny port v URL (ak API beží na porte 8080, musí byť v URL: `http://sinum.local:8080`)
   - SSL certifikát problémy (ak používate HTTPS, možno bude potrebné ignorovať certifikát)
   - API očakáva iný formát dát
   - IP adresa alebo hostname nie sú správne
   - Firewall blokuje prístup

5. **Skontrolujte dokumentáciu API**:
   - Overte presný endpoint a formát požiadavky na [apidocs.sinum.tech](https://apidocs.sinum.tech)

### Ďalšie problémy

Ak narazíte na problémy, skontrolujte:
1. Logy Home Assistant na chybové hlásenia
2. Správnosť prihlasovacích údajov
3. Dostupnosť Sinum API na zadanej adrese
4. Kompatibilitu API formátu (možno je potrebné upraviť `api.py`)
5. Sieťové pripojenie medzi Home Assistant a Sinum serverom

