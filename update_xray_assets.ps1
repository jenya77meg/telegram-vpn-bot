param(
    [string]$InstallPath = ".\volumes\xray_assets"
)

Write-Host "Downloading geoip.dat..."
Invoke-WebRequest -Uri "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geoip.dat" -OutFile "$InstallPath\geoip.dat"
Write-Host "geoip.dat downloaded."

Write-Host "Downloading geosite.dat..."
Invoke-WebRequest -Uri "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geosite.dat" -OutFile "$InstallPath\geosite.dat"
Write-Host "geosite.dat downloaded."

Write-Host "Xray assets updated successfully in $InstallPath" 