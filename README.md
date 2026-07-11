🇬🇧 [English](#english) · 🇩🇪 [Deutsch](#deutsch)

<a href="https://buymeacoffee.com/jpshub" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a> <a href="https://www.paypal.me/JPSAutomatisierung" target="_blank"><img src="https://raw.githubusercontent.com/stefan-niedermann/paypal-donate-button/master/paypal-donate-button.png" alt="Donate with PayPal" height="50" width="129"></a>

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

It connects one or two battery towers (e.g. BK215) and up to four microinverters (e.g. Deye) to achieve near-zero grid feed-in using a PID-based control loop.

---

## Requirements

- Home Assistant 2026.1 or newer
- At least one inverter with a power control entity (number entity for active power regulation or output limit percentage)
- A grid power sensor (e.g. Shelly EM)
- At least one BK215(Plus) with SOC sensor and discharge limit entities

---

## Installation

### HACS Installation (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on **Integrations**
3. Click the three dots menu in the top right corner and select **Custom repositories**
4. Add this repository URL: `https://github.com/jps-hub/ha_bk215_hybrid_controller`
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

The setup wizard has the following steps:

### Step 1 — General settings

| Field | Description | Default |
|---|---|---|
| Name | Name of the configuration entry | BK215 Hybrid Controller by JPS |
| Battery tower 1 level entity | SOC sensor of battery tower 1 | — |
| Battery cabinet discharge limit entity tower 1 | Entity for the storage discharge limit of tower 1 | — |
| Hybrid inverter discharge limit entity tower 1 | Sensor for the inverter discharge limit of tower 1, e.g. main hybrid inverter discharge limit | — |
| Power sensor entity | Grid power sensor (positive = import, negative = export) | — |
| Control interval | Execution interval of the controller in seconds | 3 s |
| Deadband minimum | Lower grid power threshold (export side) | −20 W |
| Deadband maximum | Upper grid power threshold (import side) | 20 W |
| Buffer value for discharge limit | Safety margin added to the discharge limit for the SOC check | 3 % |
| Limit for maximum inverter power limit | Hard ceiling for the max power number entity | 800 W |
| Limit for minimum inverter power limit | Hard ceiling for the max value of min inverter power | 600 W |
| Startup delay when regulating from 0% to x% | Hold time after ramping an inverter from 0 to active power | 30 s |

**Recommended deadband values by configuration:**

| Configuration | Deadband min | Deadband max |
|---|---|---|
| Deye only | −20 W | 20 W |
| 1× APsystems | −50 W | 20 W |
| 2× APsystems | −100 W | 20 W |

### Step 2 — Inverter 1 (Tower 1)

| Field | Description |
|---|---|
| Inverter type | `Deye` (output limit 0–100 %) or `APsystems` (direct watt control) |
| Entity for power control | Entity used to set the inverter output |
| Rated power | Maximum inverter power in watts |
| On/off inverter switch | Switch entity to turn the inverter on and off |
| Entity for current inverter power | Power sensor entity (required for APsystems only) |

### Step 3 — Inverter 2 (Tower 1 - optional)

Same fields as Inverter 1. Leave all fields empty if no second inverter is used.

### Step 4 — Tower 2 (optional)

Leave all fields empty if no second tower is used. Either all three fields must be filled or all must be left empty.

| Field | Description |
|---|---|
| Battery tower 2 level entity | SOC sensor of battery tower 2 |
| Battery cabinet discharge limit entity tower 2 | Entity for the storage discharge limit of tower 2 |
| Hybrid inverter discharge limit entity tower 2 | Sensor for the inverter discharge limit of tower 2 |

### Step 5 — Inverter 3 (Tower 2) — only shown if tower 2 is configured

Same fields as Inverter 1.

### Step 6 — Inverter 4 (Tower 2 - optional) — only shown if tower 2 is configured

Same fields as Inverter 1. Leave all fields empty if no fourth inverter is used.

### Step 7 — PID settings

The PID controller uses a variable proportional gain (Kp) that scales with the error magnitude. The defaults work well for most setups. When tower 2 is configured, different defaults are pre-filled.

| Parameter | Default (1 tower) | Default (2 towers) | Description |
|---|---|---|---|
| Kp min | 0.4 | 0.4 | Minimum proportional gain (small errors) |
| Kp max | 0.9 | 0.65 | Maximum proportional gain (large errors) |
| Kp error scale | 600 | 600 | Error value at which Kp reaches its maximum |
| Ki | 0.02 | 0.06 | Integral gain |
| Kd | 0.12 | 0.55 | Derivative gain |
| Kd error scale | 300 | 300 | Error scale for derivative gain reduction |
| Kd dt reference | 3 | 2 | Reference time step for derivative normalisation |
| Kd max | 0.35 | 0.35 | Maximum derivative contribution |

---

## Entities

### Switches (config category)

| Entity | Description |
|---|---|
| **Automatic** | Enables or disables the control loop. Persisted across restarts. |
| **Boost** | Sets all active inverters to their rated power immediately. Only available when Automatic is on. |
| **Inverter 1 manual disable** | Puts inverter 1 into manual mode. The inverter is switched off and can then be controlled outside the integration. |
| **Inverter 2 manual disable** | Puts inverter 2 into manual mode. Same behaviour (only shown if configured). |
| **Inverter 3 manual disable** | Puts inverter 3 into manual mode. Same behaviour (only shown if configured). |
| **Inverter 4 manual disable** | Puts inverter 4 into manual mode. Same behaviour (only shown if configured). |
| **Inverter 1 helper** | Internal on/off state tracked by the controller for inverter 1 (hidden by default). |
| **Inverter 2 helper** | Whether the controller considers inverter 2 to be on (only shown if configured, hidden by default). |
| **Inverter 3 helper** | Whether the controller considers inverter 3 to be on (only shown if configured, hidden by default). |
| **Inverter 4 helper** | Whether the controller considers inverter 4 to be on (only shown if configured, hidden by default). |

### Numbers (config category)

| Entity | Unit | Description |
|---|---|---|
| **Feed-in start threshold tower 1** | % | Minimum SOC of tower 1 required before the controller starts inverters 1/2. |
| **Feed-in start threshold tower 2** | % | Minimum SOC of tower 2 required before the controller starts inverters 3/4 (only shown if tower 2 configured). |
| **Max inverter power** | W | Upper power limit sent to inverters. Capped by the configured max power limit. |
| **Min inverter power** | W | Lower power limit; prevents inverters from operating below a useful threshold. |
| **Power sensor offset** | W | Correction value added to/subtracted from the grid power reading. |
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
| `Battery level low` | SOC of both towers below discharge limit + buffer; all inverters shut down. |
| `Tower 1 battery level low` | SOC of tower 1 below limit; inverters 1/2 shut down, tower 2 continues. |
| `Tower 2 battery level low` | SOC of tower 2 below limit; inverters 3/4 shut down, tower 1 continues. |
| `Failure` | Inverters are unexpectedly off during normal operation. |
| `Inverter 1 on, inverter 2 failure` | Inverter 2 turned off unexpectedly; controller continues with inverter 1 only. |
| `Inverter 2 on, inverter 1 failure` | Inverter 1 turned off unexpectedly; controller continues with inverter 2 only. |
| `Inverter 3 on, inverter 4 failure` | Inverter 4 turned off unexpectedly; controller continues with inverter 3 only. |
| `Inverter 4 on, inverter 3 failure` | Inverter 3 turned off unexpectedly; controller continues with inverter 4 only. |
| `Inverter 1 manual` | Inverter 1 in manual mode. |
| `Inverter 1 manual, inverter 2 on` | Inverter 1 in manual mode; controller continues with inverter 2 only. |
| `Inverter 2 manual` | Inverter 2 in manual mode. |
| `Inverter 2 manual, inverter 1 on` | Inverter 2 in manual mode; controller continues with inverter 1 only. |
| `Inverter 3 manual` | Inverter 3 in manual mode. |
| `Inverter 3 manual, inverter 4 on` | Inverter 3 in manual mode; controller continues with inverter 4 only. |
| `Inverter 4 manual` | Inverter 4 in manual mode. |
| `Inverter 4 manual, inverter 3 on` | Inverter 4 in manual mode; controller continues with inverter 3 only. |
| `Both inverters tower 1 manual` | Both tower 1 inverters in manual mode. |
| `Both inverters tower 2 manual` | Both tower 2 inverters in manual mode. |
| `All inverters manual` | All inverters in manual mode. |

### Binary sensors (diagnostic category)

| Entity | Description |
|---|---|
| **Automatic** | Mirrors the Automatic switch state. |
| **Boost** | Mirrors the Boost switch state. |
| **Inverter 1 helper** | Whether the controller considers inverter 1 to be on. |
| **Inverter 1 manual** | Mirrors the inverter 1 manual disable switch state. |
| **Inverter 1 switch** | Mirrors the actual state of the external inverter 1 switch. |
| **Inverter 2 helper** | Whether the controller considers inverter 2 to be on (only shown if configured). |
| **Inverter 2 manual** | Mirrors the inverter 2 manual disable switch state (only shown if configured). |
| **Inverter 2 switch** | Mirrors the actual state of the external inverter 2 switch (only shown if configured). |
| **Inverter 3 helper** | Whether the controller considers inverter 3 to be on (only shown if configured). |
| **Inverter 3 manual** | Mirrors the inverter 3 manual disable switch state (only shown if configured). |
| **Inverter 3 switch** | Mirrors the actual state of the external inverter 3 switch (only shown if configured). |
| **Inverter 4 helper** | Whether the controller considers inverter 4 to be on (only shown if configured). |
| **Inverter 4 manual** | Mirrors the inverter 4 manual disable switch state (only shown if configured). |
| **Inverter 4 switch** | Mirrors the actual state of the external inverter 4 switch (only shown if configured). |

---

## Control logic

```
Every <interval> seconds (and on relevant state changes):

1. Tower 1 and tower 2 start checks run independently:
   - If avg_soc_n >= charge_limit_start_n and outside protection zone
     → start inverters of that tower if not already on
2. Calculate system state (protection check):
   - avg_soc_1 <= discharge_limit_1 + buffer  →  tower1_soc_low  →  shut down WR1+WR2
   - avg_soc_2 <= discharge_limit_2 + buffer  →  tower2_soc_low  →  shut down WR3+WR4
   - Both towers low                           →  soc_low         →  shut down all
   - Inverter unexpectedly off                 →  failure state
3. If system state is soc_low / inv_off / failure / both_manual:
   - Set all inverter outputs to 0, turn off switches
4. If Boost mode:
   - Set all active inverters to rated power (up to max_power_inverter)
5. Otherwise (PID mode):
   - Deadband check: if grid power is within [deadband_min, deadband_max]  →  idle
   - PID step: calculate target power from grid error
   - Split target proportionally between all active inverters by rated power
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

- Home Assistant 2026.1 oder neuer
- Mindestens ein Wechselrichter mit einer Leistungssteuerungs-Entity (Number-Entity für aktive Leistungsregelung oder Ausgangsbegrenzung in Prozent)
- Ein Netzleistungssensor (z. B. Shelly EM)
- Mindestens ein BK215(Plus) mit SOC-Sensor und Entladegrenzen-Entities des Speichers

---

## Installation

### HACS-Installation (Empfohlen)

1. HACS in deiner Home Assistant-Instanz öffnen
2. Auf **Integrationen** klicken
3. Das Drei-Punkte-Menü oben rechts öffnen und **Benutzerdefinierte Repositories** auswählen
4. Diese Repository-URL hinzufügen: `https://github.com/jps-hub/ha_bk215_hybrid_controller`
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
4. Die Integration über die UI hinzufügen: **Einstellungen** → **Geräte & Dienste** → **Integration hinzufügen** → Nach "BK215 Hybrid Controller" suchen

---

## Einrichtung

Der Einrichtungsassistent umfasst folgende Schritte:

### Schritt 1 — Allgemeine Einstellungen

| Feld | Beschreibung | Standard |
|---|---|---|
| Name | Name des Konfigurationseintrags | BK215 Hybrid Controller by JPS |
| Entität Speicherlevel Turm 1 | SOC-Sensor des Batteriespeichers Turm 1 | — |
| Entität BK Entladegrenze Turm 1 | Entität für die Speicher-Entladegrenze Turm 1 | — |
| Entität HW-Entladegrenze Turm 1 z.B. Kopf HW-Entladegrenze | Sensor HW-Entladegrenze Turm 1 | — |
| Entität Shelly oder anderer Sensor für die aktuelle Leistung | Netzleistungssensor | — |
| Regelintervall | Ausführungsintervall des Controllers in Sekunden | 3 s |
| Deadband-Minimum | Untere Netzleistungsschwelle | −20 W |
| Deadband-Maximum | Obere Netzleistungsschwelle | 20 W |
| Pufferwert für Entladegrenze | Sicherheitspuffer, der zur Entladegrenze für die SOC-Prüfung addiert wird | 3 % |
| Limit für Maximale Wechselrichter-Leistungsgrenze | Feste Obergrenze für den Maximalwert der Max WR-Leistung | 800 W |
| Limit für Minimale Wechselrichter-Leistungsgrenze | Feste Obergrenze für den Maximalwert der Min WR-Leistung | 600 W |
| Anlaufverzögerung bei Regelung von 0% auf x% | Haltezeit nach dem Hochregeln eines Wechselrichters von 0 auf aktive Leistung | 30 s |

**Empfohlene Deadband-Werte je Konfiguration:**

| Konfiguration | Deadband-Min | Deadband-Max |
|---|---|---|
| Nur Deye | −20 W | 20 W |
| 1× APsystems | −50 W | 20 W |
| 2× APsystems | −100 W | 20 W |

### Schritt 2 — Wechselrichter 1 (Turm 1)

| Feld | Beschreibung |
|---|---|
| Wechselrichtertyp | `Deye` (Ausgangsbegrenzung 0–100 %) oder `APsystems` (direkte Watt-Steuerung) |
| Entität zur Leistungssteuerung | Entität zum Einstellen der Ausgangsleistung |
| Nennleistung | Maximale Wechselrichterleistung in Watt |
| Ein/Aus-Schalter Wechselrichter | Schalterentität zum Ein- und Ausschalten des Wechselrichters |
| Entität für aktuelle Leistung Wechselrichter | Leistungssensorentität Wechselrichter (nur für APsystems erforderlich) |

### Schritt 3 — Wechselrichter 2 (Turm 1 - optional)

Gleiche Felder wie bei Wechselrichter 1. Alle Felder leer lassen, wenn kein zweiter Wechselrichter verwendet wird.

### Schritt 4 — Turm 2 (optional)

Alle Felder leer lassen, wenn kein zweiter Turm verwendet wird.

| Feld | Beschreibung |
|---|---|
| Entität Speicherlevel Turm 2 (optional) | SOC-Sensor des Batteriespeichers Turm 2 |
| Entität BK Entladegrenze Turm 2 (optional) | Entität für die Speicher-Entladegrenze Turm 2 |
| Entität HW-Entladegrenze Turm 2 z.B. Kopf HW-Entladegrenze (optional) | Sensor HW-Entladegrenze Turm 2 |

### Schritt 5 — Wechselrichter 3 (Turm 2) - Wird nur angezeigt, wenn Turm 2 konfiguriert wurde

| Feld | Beschreibung |
|---|---|
| Wechselrichtertyp | `Deye` (Ausgangsbegrenzung 0–100 %) oder `APsystems` (direkte Watt-Steuerung) |
| Entität zur Leistungssteuerung | Entität zum Einstellen der Ausgangsleistung |
| Nennleistung | Maximale Wechselrichterleistung in Watt |
| Ein/Aus-Schalter Wechselrichter | Schalterentität zum Ein- und Ausschalten des Wechselrichters |
| Entität für aktuelle Leistung Wechselrichter | Leistungssensorentität Wechselrichter (nur für APsystems erforderlich) |

### Schritt 6 — Wechselrichter 4 (Turm 2 - optional) - Wird nur angezeigt, wenn Turm 2 konfiguriert wurde

| Feld | Beschreibung |
|---|---|
| Wechselrichtertyp | `Deye` (Ausgangsbegrenzung 0–100 %) oder `APsystems` (direkte Watt-Steuerung) |
| Entität zur Leistungssteuerung | Entität zum Einstellen der Ausgangsleistung |
| Nennleistung | Maximale Wechselrichterleistung in Watt |
| Ein/Aus-Schalter Wechselrichter | Schalterentität zum Ein- und Ausschalten des Wechselrichters |
| Entität für aktuelle Leistung Wechselrichter | Leistungssensorentität Wechselrichter (nur für APsystems erforderlich) |

### Schritt 7 — PID-Einstellungen

Der PID-Regler verwendet einen variablen Proportionalanteil (Kp), der mit der Fehlergröße skaliert. Die Standardwerte funktionieren für die meisten Setups gut.


| Parameter | Standard (Ein Turm) | Standard (Zwei Türme) | Beschreibung |
|---|---|---|---|
| Kp min | 0.4 | 0.4 | Minimaler Proportionalanteil (kleine Fehler) |
| Kp max | 0.9 | 0.65 | Maximaler Proportionalanteil (große Fehler) |
| Kp-Fehlerskalierung | 600 | 600 | Fehlerwert, bei dem Kp sein Maximum erreicht |
| Ki | 0.02 | 0.06 | Integralanteil |
| Kd | 0.12 | 0.55 | Differenzialanteil |
| Kd-Fehlerskalierung | 300 | 300 | Fehlerskalierung zur Reduzierung des Differenzialanteils |
| Kd-dt-Referenz | 3 | 2 | Referenzzeitschritt für die Differenzial-Normalisierung |
| Kd max | 0.35 | 0.35 | Maximaler Differenzialbeitrag |

---

## Entities

### Schalter (Konfigurationskategorie)

| Entity | Beschreibung |
|---|---|
| **Automatik** | Aktiviert oder deaktiviert den Regelkreis. Wird bei Neustart gespeichert. |
| **Boost** | Setzt alle aktiven Wechselrichter sofort auf Nennleistung. Nur bei eingeschalteter Automatik verfügbar. |
| **WR 1 manuell** | Schaltet den Wechselrichter 1 auf manuellen Betrieb. Wechselrichter wird abgeschaltet und kann anschließend außerhalb der Integration gesteuert werden |
| **WR 2 manuell** | Schaltet den Wechselrichter 2 auf manuellen Betrieb. Wechselrichter wird abgeschaltet und kann anschließend außerhalb der Integration gesteuert werden (nur bei konfiguriertem Wechselrichter sichtbar). |
| **WR 3 manuell** | Schaltet den Wechselrichter 3 auf manuellen Betrieb. Wechselrichter wird abgeschaltet und kann anschließend außerhalb der Integration gesteuert werden (nur bei konfiguriertem Wechselrichter sichtbar). |
| **WR 4 manuell** | Schaltet den Wechselrichter 4 auf manuellen Betrieb. Wechselrichter wird abgeschaltet und kann anschließend außerhalb der Integration gesteuert werden (nur bei konfiguriertem Wechselrichter sichtbar). |
| **WR 1 Helfer** | Interner Ein/Aus-Status des Controllers für Wechselrichter 1. |
| **WR 2 Helfer** | Interner Ein/Aus-Status des Controllers für Wechselrichter 2 (nur bei konfiguriertem Wechselrichter sichtbar). |
| **WR 3 Helfer** | Interner Ein/Aus-Status des Controllers für Wechselrichter 3 (nur bei konfiguriertem Wechselrichter sichtbar). |
| **WR 4 Helfer** | Interner Ein/Aus-Status des Controllers für Wechselrichter 4 (nur bei konfiguriertem Wechselrichter sichtbar). |

### Zahlenwerte (Konfigurationskategorie)

| Entity | Einheit | Beschreibung |
|---|---|---|
| **Startwert Einspeisung** | % | Mindest-SOC, bevor der Controller die Wechselrichter startet. |
| **Max WR-Leistung** | W | Obere Leistungsgrenze für die Wechselrichter. Begrenzt durch das konfigurierte Leistungslimit. |
| **Min WR-Leistung** | W | Untere Leistungsgrenze; verhindert den Betrieb unterhalb einer sinnvollen Schwelle. |
| **Offset Leistungssensor** | W | Korrekturwert, der zum Netzleistungsmesswert addiert/subtrahiert wird. |
| **Deadband min** | W | Untere Deadband Grenze (Einspeiseseite). |
| **Deadband max** | W | Obere Deadband Grenze (Bezugsseite). |

### Sensoren (Diagnosekategorie)

| Entity | Beschreibung |
|---|---|
| **Systemstatus** | Aktueller Schutz-/Betriebszustand (siehe Tabelle unten). |
| **Deadban-Status** | Ob der Controller im Modus `Neutral`, `Bezug` oder `Einspeisung` ist. |
| **Integralwert** | Aktueller PID-Integralterm (W). |
| **Letzter Zielwert** | Letzter Leistungs-Sollwert, der an die Wechselrichter gesendet wurde (W). |
| **Letzter Fehler** | Letzter vom PID verwendeter Fehlerwert (W). |
| **Gefilterter Fehler** | Deadband korrigierter Fehler, der in den PID eingespeist wird (W). |

**Systemzustandswerte:**

| Zustand | Bedeutung |
|---|---|
| `Inaktiv` | Automatik ist ausgeschaltet. |
| `WR aus` | SOC unter der Startschwelle; Wechselrichter sind aus. |
| `WR an` | Normalbetrieb; alle konfigurierten Wechselrichter laufen. |
| `Speicherstand niedrig` | SOC beider Türme unter Entladegrenze + Puffer; Wechselrichter wurden abgeschaltet. |
| `Turm 1 Speicherstand niedrig` | SOC Turm 1 unter Entladegrenze + Puffer; Wechselrichter wurden abgeschaltet. |
| `Turm 2 Speicherstand niedrig` | SOC Turm 2 unter Entladegrenze + Puffer; Wechselrichter wurden abgeschaltet. |
| `Fehler` | Beide Wechselrichter sind während des Normalbetriebs unerwartet ausgefallen. |
| `WR 1 an, WR 2 Fehler` | WR 2 hat sich unerwartet ausgeschaltet; Controller läuft nur mit WR 1 weiter. |
| `WR 2 an, WR 1 Fehler` | WR 1 hat sich unerwartet ausgeschaltet; Controller läuft nur mit WR 2 weiter. |
| `WR 3 an, WR 4 Fehler` | WR 4 hat sich unerwartet ausgeschaltet; Controller läuft nur mit WR 3 weiter. |
| `WR 4 an, WR 3 Fehler` | WR 3 hat sich unerwartet ausgeschaltet; Controller läuft nur mit WR 4 weiter. |
| `WR 1 manuell` | WR 1 auf manuellen Betrieb gestellt. |
| `WR 1 manuell, WR 2 an` | WR 1 auf manuellen Betrieb gestellt; Controller läuft nur mit WR 2 weiter. |
| `WR 2 manuell` | WR 2 auf manuellen Betrieb gestellt. |
| `WR 2 manuell, WR 1 an` | WR 2 auf manuellen Betrieb gestellt; Controller läuft nur mit WR 1 weiter. |
| `WR 3 manuell` | WR 3 auf manuellen Betrieb gestellt. |
| `WR 3 manuell, WR 4 an` | WR 3 auf manuellen Betrieb gestellt; Controller läuft nur mit WR4 weiter. |
| `WR 4 manuell` | WR 4 auf manuellen Betrieb gestellt. |
| `WR 4 manuell, WR 3 an` | WR 4 auf manuellen Betrieb gestellt; Controller läuft nur mit WR 3 weiter. |
| `Beide WR Turm 1 manuell` | Beide WR Turm 1 auf manuellen Betrieb gestellt. |
| `Beide WR Turm 2 manuell` | Beide WR Turm 2 auf manuellen Betrieb gestellt. |
| `Alle WR manuell` | Alle WR auf manuellen Betrieb gestellt. |

### Binärsensoren (Diagnosekategorie)

| Entity | Beschreibung |
|---|---|
| **Automatik** | Spiegelt den Automatik-Schalter-Status. |
| **Boost** | Spiegelt den Boost-Schalter-Status. |
| **WR 1 Helfer** | Status des Helfers, spiegelt ob der Controller WR1 als eingeschaltet betrachtet. |
| **WR 1 manuell** | Spiegelt den WR 1 manuell-Schalter-Status |
| **WR 1 Schalter** | Spiegelt den Status des externen Wechselrichterschalter. |
| **WR 2 Helfer** | Status des Helfers, spiegelt ob der Controller WR 2 als eingeschaltet betrachtet (nur bei konfiguriertem Wechselrichter sichtbar). |
| **WR 2 manuell** | Spiegelt den WR 2 manuell-Schalter-Status (nur bei konfiguriertem Wechselrichter sichtbar). |
| **WR 2 Schalter** | Spiegelt den Status des externen Wechselrichterschalters (nur bei konfiguriertem Wechselrichter sichtbar). |
| **WR 3 Helfer** | Status des Helfers, spiegelt ob der Controller WR 3 als eingeschaltet betrachtet (nur bei konfiguriertem Wechselrichter sichtbar). |
| **WR 3 manuell** | Spiegelt den WR 3 manuell-Schalter-Status (nur bei konfiguriertem Wechselrichter sichtbar). |
| **WR 3 Schalter** | Spiegelt den Status des externen Wechselrichterschalters (nur bei konfiguriertem Wechselrichter sichtbar). |
| **WR 4 Helfer** | Status des Helfers, spiegelt ob der Controller WR 4 als eingeschaltet betrachtet (nur bei konfiguriertem Wechselrichter sichtbar). |
| **WR 4 manuell** | Spiegelt den WR 4 manuell-Schalter-Status (nur bei konfiguriertem Wechselrichter sichtbar). |
| **WR 4 Schalter** | Spiegelt den Status des externen Wechselrichterschalters (nur bei konfiguriertem Wechselrichter sichtbar). |

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

