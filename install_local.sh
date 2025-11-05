#!/bin/bash
# Script na lokálnu inštaláciu Sinum integrácie do Home Assistant

# Konfigurácia - upravte podľa vašich potrieb
PROJECT_DIR="/Users/dbaranec/Workspace/sinum"
HA_IP="192.168.1.50"
HA_USER="root"  # Zvyčajne 'root' pre Home Assistant OS
HA_CONFIG_DIR="/config"  # Štandardná cesta pre Home Assistant OS

# Miestny prístup (ak máte mountovaný config adresár)
# HA_CONFIG_DIR="${HOME}/.homeassistant"  # Pre lokálny venv
# HA_CONFIG_DIR="/config"  # Pre Docker (ak je mountovaný)

# Sieťový prístup cez SSH
USE_SSH=true  # Nastavte na false ak používate lokálny alebo mountovaný adresár

echo "🚀 Lokálna inštalácia Sinum integrácie"
echo "======================================"
echo ""
echo "Project directory: $PROJECT_DIR"
echo "HA IP: $HA_IP"
echo "HA config directory: $HA_CONFIG_DIR"
echo ""

# Skontrolujte či existuje projekt
if [ ! -d "$PROJECT_DIR/custom_components/sinum" ]; then
    echo "❌ Chyba: Projekt nebol nájdený v $PROJECT_DIR/custom_components/sinum"
    exit 1
fi

if [ "$USE_SSH" = true ]; then
    echo "📡 Použitie SSH prístupu na $HA_IP..."
    echo ""
    
    # Test SSH pripojenia
    if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "$HA_USER@$HA_IP" exit 2>/dev/null; then
        echo "⚠️  Varovanie: SSH pripojenie zlyhalo alebo vyžaduje heslo"
        echo ""
        echo "Použite jeden z týchto prístupov:"
        echo ""
        echo "1. SSH s hesľom (budete vyzvaní):"
        echo "   ssh $HA_USER@$HA_IP"
        echo ""
        echo "2. Alebo skopírujte súbory manuálne cez SSH:"
        echo "   scp -r $PROJECT_DIR/custom_components/sinum $HA_USER@$HA_IP:$HA_CONFIG_DIR/custom_components/"
        echo ""
        echo "3. Alebo použite Samba share (ak je povolený):"
        echo "   Connect to: smb://$HA_IP/config"
        echo ""
        exit 1
    fi
    
    # Vytvorte priečinok cez SSH
    ssh "$HA_USER@$HA_IP" "mkdir -p $HA_CONFIG_DIR/custom_components"
    
    # Skopírujte súbory cez SSH
    echo "📦 Kopírovanie súborov cez SSH..."
    scp -r "$PROJECT_DIR/custom_components/sinum" "$HA_USER@$HA_IP:$HA_CONFIG_DIR/custom_components/"
    
    if [ $? -eq 0 ]; then
        echo "✅ Integrácia bola úspešne skopírovaná!"
        echo ""
        echo "📝 Ďalšie kroky:"
        echo "1. Reštartujte Home Assistant cez UI alebo SSH:"
        echo "   ssh $HA_USER@$HA_IP 'ha core restart'"
        echo "2. Prejdite do Nastavenia → Zariadenia a služby"
        echo "3. Kliknite na 'Pridať integráciu'"
        echo "4. Vyhľadajte 'Sinum'"
    else
        echo "❌ Chyba pri kopírovaní súborov cez SSH"
        exit 1
    fi
else
    echo "📁 Použitie lokálneho/mountovaného adresára..."
    echo ""
    
    # Vytvorte custom_components priečinok ak neexistuje
    mkdir -p "$HA_CONFIG_DIR/custom_components"
    
    # Skopírujte integráciu
    echo "📦 Kopírovanie súborov..."
    cp -r "$PROJECT_DIR/custom_components/sinum" "$HA_CONFIG_DIR/custom_components/"
    
    if [ $? -eq 0 ]; then
        echo "✅ Integrácia bola úspešne skopírovaná!"
        echo ""
        echo "📝 Ďalšie kroky:"
        echo "1. Reštartujte Home Assistant"
        echo "2. Prejdite do Nastavenia → Zariadenia a služby"
        echo "3. Kliknite na 'Pridať integráciu'"
        echo "4. Vyhľadajte 'Sinum'"
    else
        echo "❌ Chyba pri kopírovaní súborov"
        exit 1
    fi
fi

echo ""
echo "💡 Tip: Pre automatické aktualizácie použite symlink (cez SSH alebo lokálne)"

