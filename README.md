🇬🇧 [English](#english) · 🇩🇪 [Deutsch](#deutsch)

---

<a name="english"></a>

# BK215 Hybrid Controller by JPS

> ⚠️ **EXPERIMENTAL INTEGRATION — USE AT YOUR OWN RISK**
>
> This is an **unofficial** custom integration for Home Assistant to control SunEnergyXT systems.
> This integration is not affiliated with SunEnergyXT.
>
> **No warranty or support is provided. Use of this integration is entirely at your own risk.**

A Home Assistant custom integration that replaces the script-based JPS controller with a fully integrated, UI-configurable controller.

It connects a battery tower (e.g. BK215) and one or two microinverters (e.g. Deye) to achieve
near-zero grid feed-in using a PID-based control loop.

---

## Requirements

- Home Assistant 2024.1 or newer
- At least one inverter that exposes a power control entity (number entity for
  active power regulation or output limit percentage)
- A grid power sensor (e.g. Shelly EM)
- A battery SOC sensor
- Discharge limit entities for the battery cabinet and the hybrid inverter

---

## Installation

### HACS Installation (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on **Integrations**
3. Click the three dots menu in the top right corner and select **Custom repositories**
4. Add this repository URL: `https://github.com/jps-hub/bk215_hybrid_controller`
5. Select **Integration** as the category
6. Click **Add**
7. Search for "BK215 Hybrid Controller by JPS" in HACS
8. Click **Download** and select the latest version
9. Restart Home Assistant
10. Add the integration through the UI: **Settings** → **Devices & Services** → **Add Integration** → Search for "BK215 Hybrid Controller by JPS"

### Manual Installation

1. Download or clone this repository
2. Copy the `bk215_hybrid_controller` folder to your Home Assistant configuration directory:
   ```
   config/custom_components/bk215_hybrid_controller/
   ```
3. Restart Home Assistant
4. Add the integration through the UI: **Settings** → **Devices & Services** → **Add Integration** → Search for "BK215 Hybrid Controller by JPS"

---

## Setup

The setup wizard has four steps:

### Step 1 — General settings

| Field | Description | Default |
|---|---|---|
| Battery tower level entity | SOC sensor of the battery tower | — |
| Battery cabinet discharge limit entity | Number entity for the battery discharge limit | — |
| Hybrid inverter discharge limit entity | Sensor or number entity for the inverter discharge limit | — |
| Power sensor entity | Grid power sensor (positive = import, negative = export) | — |
| Control interval | How often the controller runs in seconds | 3 s |
| Deadband minimum | Lower grid power threshold before the controller acts (export side) | −20 W |
| Deadband maximum | Upper grid power threshold before the controller acts (import side) | 20 W |
| Buffer SOC | Safety margin added to the discharge limit for the SOC check | 3 % |
| Limit for the maximum inverter power limit | Hard ceiling for the max power number entity | 800 W |
| Limit for the minimum inverter power limit | Hard floor for the min power number entity | 600 W |
| Startup delay | Hold time after ramping an inverter from 0 to active power | 30 s |

**Recommended deadband values by configuration:**

| Configuration | Deadband min | Deadband max |
|---|---|---|
| Deye only | −20 W | 20 W |
| 1× APsystems | −50 W | 20 W |
| 2× APsystems | −100 W | 20 W |

### Step 2 — Inverter 1

| Field | Description |
|---|---|
| Inverter type | `Deye` (output limit 0–100 %) or `APsystems` (direct watt control) |
| Entity for power control | Number entity used to set the inverter output |
| Rated power | Maximum inverter power in watts |
| On/off inverter switch | Switch entity to turn the inverter on and off |
| Current inverter power entity | Power sensor (required for APsystems only) |

### Step 3 — Inverter 2 (optional)

Same fields as Inverter 1. Leave all fields empty if no second inverter is used.

### Step 4 — PID settings

The PID controller uses a variable proportional gain (Kp) that scales with the
error magnitude. Advanced users can adjust the parameters here; the defaults
work well for most setups.

| Parameter | Default | Description |
|---|---|---|
| Kp min | 0.4 | Minimum proportional gain (small errors) |
| Kp max | 0.9 | Maximum proportional gain (large errors) |
| Kp error scale | 600 | Error value at which Kp reaches its maximum |
| Ki | 0.02 | Integral gain |
| Kd | 0.12 | Derivative gain |
| Kd error scale | 300 | Error scale for derivative gain reduction |
| Kd dt reference | 3 | Reference time step for derivative normalisation |
| Kd max | 0.35 | Maximum derivative contribution |

---

## Entities

### Switches (config category)

| Entity | Description |
|---|---|
| **Automatic** | Enables or disables the control loop. Persisted across restarts. |
| **Boost** | Sets all active inverters to their rated power immediately. Only available when Automatic is on. |
| **Inverter 1 helper** | Internal on/off state tracked by the controller for inverter 1. |
| **Inverter 2 helper** | Internal on/off state tracked by the controller for inverter 2 (only shown if a second inverter is configured). |

### Numbers (config category)

| Entity | Unit | Description |
|---|---|---|
| **Feed-in start threshold** | % | Minimum SOC required before the controller starts the inverters. |
| **Max power inverter** | W | Upper power limit sent to inverters. Capped by the configured max power limit. |
| **Min power inverter** | W | Lower power limit; prevents inverters from operating below a useful threshold. |
| **Power sensor offset** | W | Correction value added to the grid sensor reading. |
| **Deadband minimum** | W | Lower deadband boundary (export side). |
| **Deadband maximum** | W | Upper deadband boundary (import side). |

### Sensors (diagnostic category)

| Entity | Description |
|---|---|
| **System state** | Current protection/operation state (see table below). |
| **Deadband state** | Whether the controller is in `neutral`, `import`, or `export` mode. |
| **Integral value** | Current PID integral term (W). |
| **Last target value** | Last power setpoint sent to the inverters (W). |
| **Last error** | Last error value used by the PID (W). |
| **Filtered error** | Deadband-adjusted error fed into the PID (W). |

**System state values:**

| State | Meaning |
|---|---|
| `Inactive` | Automatic mode is off. |
| `Inverter off` | SOC below start threshold; inverters are off. |
| `Inverter on` | Normal operation; all configured inverters are running. |
| `Battery level low` | SOC dropped below the discharge limit + buffer; inverters shut down. |
| `Failure` | Both inverters are unexpectedly off during normal operation. |
| `Inverter 1 on, inverter 2 failure` | Inverter 2 turned off unexpectedly; controller continues with inverter 1 only. |
| `Inverter 2 on, inverter 1 failure` | Inverter 1 turned off unexpectedly; controller continues with inverter 2 only. |

### Binary sensors (diagnostic category)

| Entity | Description |
|---|---|
| **Automatic active** | Mirrors the Automatic switch state. |
| **Boost active** | Mirrors the Boost switch state. |
| **Inverter 1 active** | Whether the controller considers inverter 1 to be on. |
| **Inverter 2 active** | Whether the controller considers inverter 2 to be on. |

---

## Control logic

```
Every <interval> seconds (and on relevant state changes):

1. If avg_soc >= charge_limit_start  →  start inverters if not already on
2. Calculate system state (protection check):
   - avg_soc <= discharge_limit + buffer_soc  →  soc_low  →  shut down
   - Inverter unexpectedly off                →  failure state
3. If system state is soc_low / inv_off / failure:
   - Set all inverter outputs to 0, turn off switches
4. If Boost mode:
   - Set all active inverters to rated power (up to max_power_inverter)
5. Otherwise (PID mode):
   - Deadband check: if grid power is within [deadband_min, deadband_max]  →  idle
   - PID step: calculate target power from grid error
   - Split target proportionally between active inverters by rated power
   - Apply hysteresis before writing to inverter control entities
```

---

## Options

All settings can be changed after setup via
**Settings → Devices & Services → BK215 Hybrid Controller by JPS → Configure**
without losing any other configuration. Changes trigger an automatic reload.

---

## Translations

The integration is fully translated into:
- English (`en`)
- German (`de`)

---

## Disclaimer

**This integration is provided "as is" without warranty of any kind.** The authors and contributors are not responsible for any damages or losses that may result from using this integration.

This is an experimental, unofficial integration that:

- Is not officially supported by SunEnergyXT
- May contain bugs that could affect your Home Assistant installation

**Use at your own risk and always maintain backups of your Home Assistant configuration.**

> 🤖 *This integration and its documentation were developed with the assistance of AI (GitHub Copilot / Claude). The code has been reviewed and tested, but may still contain errors.*

---

<a name="deutsch"></a>

# BK215 Hybrid Controller by JPS

> ⚠️ **EXPERIMENTELLE INTEGRATION — NUTZUNG AUF EIGENE GEFAHR**
>
> Dies ist eine **inoffizielle** Custom Integration für Home Assistant zur Steuerung von SunEnergyXT-Systemen.
> Diese Integration steht in keiner Verbindung zu SunEnergyXT.
>
> **Es wird keine Gewährleistung oder Support übernommen. Die Nutzung dieser Integration erfolgt vollständig auf eigene Gefahr.**

Eine Home Assistant Custom Integration, die die skriptbasierte JPS-Steuerung durch eine vollständig integrierte, über die UI konfigurierbare Steuerung ersetzt.

Sie verbindet einen Batteriespeicher (z. B. BK215) und ein oder zwei Mikrowechselrichter (z. B. Deye), um eine nahezu nullseitige Netzeinspeisung mithilfe eines PID-basierten Regelkreises zu erreichen.

---

## Voraussetzungen

- Home Assistant 2024.1 oder neuer
- Mindestens ein Wechselrichter mit einer Leistungssteuerungs-Entity (Number-Entity für aktive Leistungsregelung oder Ausgangsbegrenzung in Prozent)
- Ein Netzleistungssensor (z. B. Shelly EM)
- Ein Batterie-SOC-Sensor
- Entladegrenzen-Entities für Batterieschrank und Hybrid-Wechselrichter

---

## Installation

### HACS-Installation (Empfohlen)

1. HACS in deiner Home Assistant-Instanz öffnen
2. Auf **Integrationen** klicken
3. Das Drei-Punkte-Menü oben rechts öffnen und **Benutzerdefinierte Repositories** auswählen
4. Diese Repository-URL hinzufügen: `https://github.com/jps-hub/bk215_hybrid_controller`
5. Als Kategorie **Integration** auswählen
6. Auf **Hinzufügen** klicken
7. In HACS nach "BK215 Hybrid Controller by JPS" suchen
8. Auf **Herunterladen** klicken und die neueste Version auswählen
9. Home Assistant neu starten
10. Die Integration über die UI hinzufügen: **Einstellungen** → **Geräte & Dienste** → **Integration hinzufügen** → Nach "BK215 Hybrid Controller by JPS" suchen

### Manuelle Installation

1. Dieses Repository herunterladen oder klonen
2. Den Ordner `bk215_hybrid_controller` in das Home Assistant-Konfigurationsverzeichnis kopieren:
   ```
   config/custom_components/bk215_hybrid_controller/
   ```
3. Home Assistant neu starten
4. Die Integration über die UI hinzufügen: **Einstellungen** → **Geräte & Dienste** → **Integration hinzufügen** → Nach "BK215 Hybrid Controller by JPS" suchen

---

## Einrichtung

Der Einrichtungsassistent umfasst vier Schritte:

### Schritt 1 — Allgemeine Einstellungen

| Feld | Beschreibung | Standard |
|---|---|---|
| Batteriespeicher-Ladestand-Entity | SOC-Sensor des Batteriespeichers | — |
| Batterieschrank-Entladetiefe-Entity | Number-Entity für die Batterie-Entladegrenze | — |
| Hybrid-WR-Entladetiefe-Entity | Sensor oder Number-Entity für die Wechselrichter-Entladegrenze | — |
| Leistungssensor-Entity | Netzleistungssensor (positiv = Bezug, negativ = Einspeisung) | — |
| Regelintervall | Ausführungsintervall des Controllers in Sekunden | 3 s |
| Totband-Minimum | Untere Netzleistungsschwelle (Einspeiseseite) | −20 W |
| Totband-Maximum | Obere Netzleistungsschwelle (Bezugsseite) | 20 W |
| SOC-Puffer | Sicherheitspuffer, der zur Entladegrenze für die SOC-Prüfung addiert wird | 3 % |
| Limit maximale Wechselrichterleistung | Harte Obergrenze für die Max-Leistungs-Entity | 800 W |
| Limit minimale Wechselrichterleistung | Harte Untergrenze für die Min-Leistungs-Entity | 600 W |
| Anlaufverzögerung | Haltezeit nach dem Hochregeln eines Wechselrichters von 0 auf aktive Leistung | 30 s |

**Empfohlene Totband-Werte je Konfiguration:**

| Konfiguration | Totband-Min | Totband-Max |
|---|---|---|
| Nur Deye | −20 W | 20 W |
| 1× APsystems | −50 W | 20 W |
| 2× APsystems | −100 W | 20 W |

### Schritt 2 — Wechselrichter 1

| Feld | Beschreibung |
|---|---|
| Wechselrichtertyp | `Deye` (Ausgangsbegrenzung 0–100 %) oder `APsystems` (direkte Watt-Steuerung) |
| Entity für die Leistungssteuerung | Number-Entity zum Einstellen der Ausgangsleistung |
| Nennleistung | Maximale Wechselrichterleistung in Watt |
| Ein/Aus-Schalter | Switch-Entity zum Ein- und Ausschalten des Wechselrichters |
| Aktuelle Wechselrichterleistung | Leistungssensor (nur für APsystems erforderlich) |

### Schritt 3 — Wechselrichter 2 (optional)

Gleiche Felder wie bei Wechselrichter 1. Alle Felder leer lassen, wenn kein zweiter Wechselrichter verwendet wird.

### Schritt 4 — PID-Einstellungen

Der PID-Regler verwendet einen variablen Proportionalanteil (Kp), der mit der Fehlergröße skaliert. Die Standardwerte funktionieren für die meisten Setups gut.

| Parameter | Standard | Beschreibung |
|---|---|---|
| Kp min | 0.4 | Minimaler Proportionalanteil (kleine Fehler) |
| Kp max | 0.9 | Maximaler Proportionalanteil (große Fehler) |
| Kp-Fehlerskalierung | 600 | Fehlerwert, bei dem Kp sein Maximum erreicht |
| Ki | 0.02 | Integralanteil |
| Kd | 0.12 | Differenzialanteil |
| Kd-Fehlerskalierung | 300 | Fehlerskalierung zur Reduzierung des Differenzialanteils |
| Kd-dt-Referenz | 3 | Referenzzeitschritt für die Differenzial-Normalisierung |
| Kd max | 0.35 | Maximaler Differenzialbeitrag |

---

## Entities

### Schalter (Konfigurationskategorie)

| Entity | Beschreibung |
|---|---|
| **Automatik** | Aktiviert oder deaktiviert den Regelkreis. Wird bei Neustart gespeichert. |
| **Boost** | Setzt alle aktiven Wechselrichter sofort auf Nennleistung. Nur bei eingeschalteter Automatik verfügbar. |
| **Wechselrichter 1 Helfer** | Interner Ein/Aus-Status des Controllers für Wechselrichter 1. |
| **Wechselrichter 2 Helfer** | Interner Ein/Aus-Status des Controllers für Wechselrichter 2 (nur bei konfiguriertem zweiten Wechselrichter sichtbar). |

### Zahlenwerte (Konfigurationskategorie)

| Entity | Einheit | Beschreibung |
|---|---|---|
| **Einspeisung-Startschwelle** | % | Mindest-SOC, bevor der Controller die Wechselrichter startet. |
| **Max. Wechselrichterleistung** | W | Obere Leistungsgrenze für die Wechselrichter. Begrenzt durch das konfigurierte Leistungslimit. |
| **Min. Wechselrichterleistung** | W | Untere Leistungsgrenze; verhindert den Betrieb unterhalb einer sinnvollen Schwelle. |
| **Leistungssensor-Offset** | W | Korrekturwert, der zum Netzleistungsmesswert addiert wird. |
| **Totband-Minimum** | W | Untere Totband-Grenze (Einspeiseseite). |
| **Totband-Maximum** | W | Obere Totband-Grenze (Bezugsseite). |

### Sensoren (Diagnosekategorie)

| Entity | Beschreibung |
|---|---|
| **Systemzustand** | Aktueller Schutz-/Betriebszustand (siehe Tabelle unten). |
| **Totband-Zustand** | Ob der Controller im Modus `Neutral`, `Bezug` oder `Einspeisung` ist. |
| **Integralwert** | Aktueller PID-Integralterm (W). |
| **Letzter Zielwert** | Letzter Leistungs-Sollwert, der an die Wechselrichter gesendet wurde (W). |
| **Letzter Fehler** | Letzter vom PID verwendeter Fehlerwert (W). |
| **Gefilterter Fehler** | Totband-korrigierter Fehler, der in den PID eingespeist wird (W). |

**Systemzustandswerte:**

| Zustand | Bedeutung |
|---|---|
| `Inaktiv` | Automatik ist ausgeschaltet. |
| `Wechselrichter aus` | SOC unter der Startschwelle; Wechselrichter sind aus. |
| `Wechselrichter ein` | Normalbetrieb; alle konfigurierten Wechselrichter laufen. |
| `Batterie-Ladestand niedrig` | SOC unter Entladegrenze + Puffer; Wechselrichter wurden abgeschaltet. |
| `Fehler` | Beide Wechselrichter sind während des Normalbetriebs unerwartet ausgefallen. |
| `WR1 ein, WR2 ausgefallen` | WR2 hat sich unerwartet ausgeschaltet; Controller läuft nur mit WR1 weiter. |
| `WR2 ein, WR1 ausgefallen` | WR1 hat sich unerwartet ausgeschaltet; Controller läuft nur mit WR2 weiter. |

### Binärsensoren (Diagnosekategorie)

| Entity | Beschreibung |
|---|---|
| **Automatik aktiv** | Spiegelt den Automatik-Schalter-Status. |
| **Boost aktiv** | Spiegelt den Boost-Schalter-Status. |
| **Wechselrichter 1 aktiv** | Ob der Controller WR1 als eingeschaltet betrachtet. |
| **Wechselrichter 2 aktiv** | Ob der Controller WR2 als eingeschaltet betrachtet. |

---

## Steuerlogik

```
Alle <Intervall> Sekunden (und bei relevanten Zustandsänderungen):

1. Wenn avg_soc >= charge_limit_start  →  Wechselrichter starten, falls noch nicht an
2. Systemzustand berechnen (Schutzprüfung):
   - avg_soc <= Entladegrenze + SOC-Puffer  →  soc_low  →  Abschalten
   - Wechselrichter unerwartet aus          →  Fehlerzustand
3. Wenn Systemzustand soc_low / inv_off / failure:
   - Alle Wechselrichter-Ausgaben auf 0 setzen, Schalter ausschalten
4. Wenn Boost-Modus:
   - Alle aktiven Wechselrichter auf Nennleistung setzen (bis max_power_inverter)
5. Sonst (PID-Modus):
   - Totband-Prüfung: Netzleistung innerhalb [deadband_min, deadband_max]  →  Leerlauf
   - PID-Schritt: Zielleistung aus Netzfehler berechnen
   - Ziel proportional nach Nennleistung auf aktive Wechselrichter aufteilen
   - Hysterese anwenden, bevor Wechselrichter-Entities beschrieben werden
```

---

## Optionen

Alle Einstellungen können nach der Einrichtung über
**Einstellungen → Geräte & Dienste → BK215 Hybrid Controller by JPS → Konfigurieren**
geändert werden, ohne andere Konfigurationen zu verlieren. Änderungen lösen einen automatischen Neustart aus.

---

## Übersetzungen

Die Integration ist vollständig übersetzt in:
- Englisch (`en`)
- Deutsch (`de`)

---

## Haftungsausschluss

**Diese Integration wird ohne jegliche Gewährleistung bereitgestellt.** Die Autoren und Mitwirkenden übernehmen keine Haftung für Schäden oder Verluste, die durch die Nutzung dieser Integration entstehen.

Dies ist eine experimentelle, inoffizielle Integration, die:

- Nicht offiziell von SunEnergyXT unterstützt wird
- Fehler enthalten kann, die deine Home Assistant-Installation beeinträchtigen könnten

**Nutzung auf eigene Gefahr — erstelle stets Backups deiner Home Assistant-Konfiguration.**

> 🤖 *Diese Integration und ihre Dokumentation wurden mithilfe von KI (GitHub Copilot / Claude) entwickelt. Der Code wurde geprüft und getestet, kann jedoch noch Fehler enthalten.*

