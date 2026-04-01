# PMSCAN – Home Assistant Custom Integration

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![GitHub Release](https://img.shields.io/github/release/mbrentini/homeassistant_pmscan_ble.svg)](https://github.com/mbrentini/homeassistant_pmscan_ble/releases)

Intégration Home Assistant pour le capteur de particules fines **PMSCAN** (Tera Sensor / NextPM) connecté via Bluetooth BLE.

## Installation via HACS

1. Dans HACS, cliquer sur **Intégrations → ⋮ → Dépôts personnalisés**
2. Ajouter l'URL : `https://github.com/mbrentini/homeassistant_pmscan_ble` avec la catégorie **Integration**
3. Chercher **PMSCAN** dans HACS et cliquer **Télécharger**
4. Redémarrer Home Assistant

## Installation manuelle

1. Copier le dossier `custom_components/pmscan/` dans `config/custom_components/`
2. Redémarrer Home Assistant

## Configuration

1. **Paramètres → Intégrations → Ajouter → PMSCAN**
2. Cliquer **Valider** pour lancer le scan BLE
3. Sélectionner votre appareil dans la liste
4. Confirmer la connexion

## Entités créées

| Entité | Unité | Description |
|---|---|---|
| `sensor.<nom>_pm1` | µg/m³ | Particules PM1 |
| `sensor.<nom>_pm2_5` | µg/m³ | Particules PM2.5 |
| `sensor.<nom>_pm10` | pcs/L | Particules PM10 (indicatif) |
| `sensor.<nom>_rssi` | dBm | Signal Bluetooth |

## Notes

- PM1 et PM2.5 sont exprimés en µg/m³ (masse, fiable).
- PM10 est exprimé en pcs/L (nombre de particules, indicatif uniquement).
- Mise à jour toutes les 60 secondes.
- La connexion BLE se reconnecte automatiquement en cas de coupure.

## Liens

- [Rapport de bug / Feature request](https://github.com/mbrentini/homeassistant_pmscan_ble/issues)
- [Tera Sensor – NextPM](https://www.tera-sensor.com)
