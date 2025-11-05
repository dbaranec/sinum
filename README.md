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
   - **Host**: IP adresa alebo hostname vášho Sinum systému (napr. `http://192.168.1.100:8080` alebo `http://sinum.local:8080`)
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

Po úspešnej konfigurácii sa vytvoria teplotné senzory pre každú miestnosť:
- `sensor.sinum_[nazov_miestnosti]` - teplota v miestnosti

## Riešenie problémov

### Chyba "invalid_auth"

Ak dostávate chybu "invalid_auth" aj keď sú údaje správne:

1. **Zapnite debug logy** v `configuration.yaml`:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.sinum: debug
   ```

2. **Skontrolujte logy** v Home Assistant:
   - Prejdite do **Developer Tools** → **Logs**
   - Alebo Settings → System → Logs
   - Hľadajte správy obsahujúce "sinum" alebo "SinumAPI"

3. **Overte API endpoint**:
   - Skontrolujte, či API je dostupné na `http://192.168.50.231:8080/api/v1/login`
   - Môžete skúsiť otvoriť v prehliadači alebo pomocou curl:
     ```bash
     curl -X POST http://192.168.50.231:8080/api/v1/login \
       -H "Content-Type: application/json" \
       -d '{"username":"Dominik","password":"your_password"}'
     ```
   
   **Poznámka**: Ak používate `sinum.local` namiesto IP adresy:
     ```bash
     curl -X POST http://sinum.local/api/v1/login \
       -H "Content-Type: application/json" \
       -d '{"username":"Dominik","password":"your_password"}'
     ```

4. **Možné príčiny**:
   - Nesprávny endpoint (možno `/api/auth/login` namiesto `/auth/login`)
   - API očakáva iný formát dát
   - Port alebo IP adresa nie sú správne
   - Firewall blokuje prístup

5. **Skontrolujte dokumentáciu API**:
   - Overte presný endpoint a formát požiadavky
   - Možno je potrebné upraviť `api.py` podľa skutočného API

### Ďalšie problémy

Ak narazíte na problémy, skontrolujte:
1. Logy Home Assistant na chybové hlásenia
2. Správnosť prihlasovacích údajov
3. Dostupnosť Sinum API na zadanej adrese
4. Kompatibilitu API formátu (možno je potrebné upraviť `api.py`)
5. Sieťové pripojenie medzi Home Assistant a Sinum serverom

