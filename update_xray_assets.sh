#!/bin/bash

INSTALL_PATH="/opt/telegram-vpn-bot/volumes/xray_assets"

# Создаем директорию, если она не существует
mkdir -p "$INSTALL_PATH"

echo "Downloading geoip.dat..."
curl -L -o "$INSTALL_PATH/geoip.dat" "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geoip.dat"
if [ $? -eq 0 ]; then
    echo "geoip.dat downloaded successfully."
else
    echo "Failed to download geoip.dat."
    exit 1
fi

echo "Downloading geosite.dat..."
curl -L -o "$INSTALL_PATH/geosite.dat" "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geosite.dat"
if [ $? -eq 0 ]; then
    echo "geosite.dat downloaded successfully."
else
    echo "Failed to download geosite.dat."
    exit 1
fi

echo "Xray assets updated successfully in $INSTALL_PATH"
exit 0 