# Kulya Firmware

**Language / Мова:** [English](#english) | [Українська](#українська)

---

# English

## About the Project

An enhanced firmware for the Ukrainian Robotics Kulya 4.0 hexapod with improved robot behavior, configuration, and hardware setup.

## About Ukrainian Robotics – Kulya 4.0

Ukrainian Robotics – Kulya 4.0 is an open-source hexapod robot platform designed for education, robotics research, and DIY enthusiasts.

This repository is not an official Ukrainian Robotics project. It is an independent software project that extends and improves the original platform by providing alternative firmware, controllers, and software tools.

**Official project:** [Ukrainian Robotics – Kulya 4.0](https://www.ukrainerobotics.com/en/diy)

## Related Projects
| Project                      | Description                        |
| ---------------------------- | ---------------------------------- |
| [**Kulya Firmware**](https://github.com/T0riU/Kulya_Firmware)           | Robot firmware and configuration   |
| [**Kulya ESP32 Controller**](https://github.com/T0riU/Kulya_Esp32_Controller)   | ESP32 physical controller firmware |
| [**Kulya Python Controller**](https://github.com/T0riU/Kulya_Py_ControllerAndCalibration) | PC controller and calibration      |
| [**Kulya Android Controller**](https://github.com/T0riU/Kulya_Controller) | Android mobile controller          |

## Installation

Setup was done "on the knee" (quick and dirty, not a polished workflow, but it works).

1. Install [Thonny 5.0.0](https://thonny.org) — the IDE used to flash and manage the board.
2. Install the [USB → UART bridge (VCP) drivers](https://www.silabs.com/software-and-tools/usb-to-uart-bridge-vcp-drivers?tab=downloads).
3. Open Thonny and go to **Tools → Options...** ![](imagesMD/Options_Thonny.jpg).
4. Connect the ESP32 to the computer, select **MicroPython (ESP32)** as the interpreter, then click **Install or update MicroPython (esptool)** ![](imagesMD/Intepritor_Thonny.jpg).
5. In the installer, select the target port (should be detected automatically), pick the correct parameters for your specific ESP32 board, and click **Install** to flash the firmware ![](imagesMD/Firmware_Install_Thonny.jpg).
6. To access the board's file system *(screenshot placeholder: file system view)*, the following sequence is used (not necessarily "correct", but it reliably works):
   - Connect the ESP32
   - After the USB connection sound plays → press the **Stop** button (`Ctrl+F2`)
   - `Ctrl+C`
   - `Ctrl+C` again

   `Stop` triggers a soft reboot, and the two `Ctrl+C` presses interrupt the firmware's boot sequence so it doesn't start running before you can upload files.
7. Select the needed files, hold **Shift** to select them all, and click **"Upload to /"** *(screenshot placeholder: upload dialog)*.

### Wiring

![](imagesMD/board.png)

Servo wire colors: **brown = ground (–)**, **red = power (+)**, **yellow = signal (S)**.

Connect **RX/TX** on the servo controller board to **TX2/RX2** on the ESP32 — crossed over (RX↔TX) so that transmit lines feed into receive lines on each side.

| Channel (number) | Connects to | Joint |
|---|---|---|
| 1 | Right front leg (leg0) | Coxa (hip) |
| 2 | Right front leg (leg0) | Femur (thigh) |
| 3 | Right front leg (leg0) | Tibia (shin) |
| 4, 5 | — not used — | — |
| 6 | Left front leg (leg1) | Coxa |
| 7 | Left front leg (leg1) | Femur |
| 8 | Left front leg (leg1) | Tibia |
| 9 | Left middle leg (leg2) | Coxa |
| 10 | Left middle leg (leg2) | Femur |
| 11 | Left middle leg (leg2) | Tibia |
| 12, 13 | — not used — | — |
| 14 | Left rear leg (leg3) | Coxa |
| 15 | Left rear leg (leg3) | Femur |
| 16 | Left rear leg (leg3) | Tibia |
| 17 | Right rear leg (leg4) | Coxa |
| 18 | Right rear leg (leg4) | Femur |
| 19 | Right rear leg (leg4) | Tibia |
| 20, 21 | — not used — | — |
| 22 | Right middle leg (leg5) | Coxa |
| 23 | Right middle leg (leg5) | Femur |
| 24 | Right middle leg (leg5) | Tibia |

## How It Works

### Startup

**`boot.py`** — the first script executed when the board powers on. It waits 3 seconds (to allow interrupting the boot process via the REPL if you need to re-flash), then imports `run.py`.

**`run.py`** — brings up all subsystems in order:
1. `esp_legs_setup` — creates 6 `Leg` objects
2. `esp_ble.ESP32_BLE(...)` — starts the BLE server (advertising, command receiver)
3. `esp_now_rx` + a hardware timer — the ESP-NOW receiver (physical remote), polled every 50 ms
4. `esp_legmover.legmover` — a separate thread (`_thread`) that continuously computes angles → sends them to the servo controller over UART
5. `esp_gait_selector.gait_selector()` — the main infinite loop, the command dispatcher

### Shared State

**`esp_context.py`** — the single source of truth. The `RC_data` dictionary holds all control parameters (see the command table below). It is read and written by every other module. It also holds: `legmover_on` (a flag for whether the leg-movement thread is active), `ble_instance` (a reference to the BLE object so gaits can send replies), and `motion_smooth_rate` (how smoothly motion is interpolated when `speed:0`).

**`esp_parse_update.py`** — parses incoming commands. Splits `param:value;...` into pairs and writes them into `RC_data`. It also has special handling for `J_XY` (joystick) — it converts `x|y` (-100..100) into `dx/dy/speed/turn_angle` or `rx/ry`, depending on `J_mode` (`steer` / `sides` / `shift` / `tilt`).

### Communication

**`esp_ble.py`** — the BLE server (Nordic UART Service). It receives commands, **buffers incoming chunks and only parses them once it encounters `\n`** (without this, long commands would get cut off by the ~20-byte MTU limit). The `ESP32_BLE` class registers itself in `esp_context.ble_instance` so other modules can send replies through `.send(text)`. The on-board LED blinks until a connection is established, and stays solid once connected.

**`esp_now_rx.py`** — the ESP-NOW receiver, used for the physical remote (not BLE). Each packet is a complete, standalone command (unlike BLE, ESP-NOW doesn't split messages into chunks).

### Kinematics and Movement

**`esp_Leg_class.py`** — the `Leg` class: geometry (segment lengths, angle limits per joint), servo pins, `invert` (whether to mirror the pulse on a given joint), and current/target/previous angles. It **does not know** the direction the legs are traversed around the body — the angle (`leg_angle`) is passed in from outside, computed by `esp_legs_setup.py`.

**`esp_inverse_kinematics.py`** — inverse kinematics. `IK(leg, xyz)` converts coordinates into joint angles (clamped to the leg's limits). `getSpread_xyz(...)` converts stance parameters (spread/height/tilt/turn) into target leg coordinates.

**`esp_legmover.py`** — a dedicated thread. Every `espi` ms it interpolates `current_angles` → `target_angles` (stepwise if `speed > 0`, smoothly if `speed:0`), builds a command string for the ch24 servo controller, and sends it over UART. It also contains `deg2pulse()` with a **hard clamp of 500–2500 μs** (no calibration value or angle can push a servo outside a safe range).

**`esp_legs_setup.py`** — creates the 6 `Leg` objects, all sourced from JSON files (see the config section below). If `legs_config.json` is missing or corrupted, there's a minimal built-in fallback (matching the robot's original wiring) so the board can still boot, along with a warning in the REPL.

### Gaits (`esp_gait_*.py`)

Each file implements one `gait:NAME;` command, registered in `esp_gait_selector.py`. See the command table below for details.

**`esp_gait_selector.py`** — the main dispatcher. Reads `RC_data["gait"]` and calls the corresponding function. It's wrapped in a `try/except` — if a gait raises an exception, the dispatcher doesn't die permanently; it rolls `gait` back to `STOP` and prints the reason to the REPL.

### JSON Configuration Files — Changeable Without Reflashing

#### `legs_config.json` — hardware wiring (not written by code automatically, edit by hand)

```json
{
  "legs_clockwise": false,
  "0": {"pins": [1, 2, 3],    "invert": [true, false, true]},
  "1": {"pins": [6, 7, 8],    "invert": [true, false, true]},
  "2": {"pins": [9, 10, 11],  "invert": [true, false, true]},
  "3": {"pins": [14, 15, 16], "invert": [true, false, true]},
  "4": {"pins": [17, 18, 19], "invert": [true, false, true]},
  "5": {"pins": [22, 23, 24], "invert": [true, false, true]}
}
```

- **`legs_clockwise`** (`true`/`false`) — the direction legs are traversed around the body (clockwise or counter-clockwise). Flipping this one value inverts the order of all six angles at once. Check it by turning during `WALK` — if the robot turns the wrong way, flip this value.
- **`"0".."5"`** — one entry per leg:
  - `pins` — `[coxa_pin, femur_pin, tibia_pin]`, the channels on the ch24 servo controller
  - `invert` — `[coxa, femur, tibia]`, whether to mirror (`3000 - pulse`) the pulse on that joint of that leg. Needed when servos on different legs are physically mounted differently.

Read once at startup — changes require rebooting the board.

#### `calibration.json` — calibration (written automatically by the `SAVE` gait)

```json
{"0": [0, 0, 0], "1": [0, 0, 0], "2": [0, 0, 0], "3": [0, 0, 0], "4": [0, 0, 0], "5": [0, 0, 0]}
```

`{"leg_num": [coxa_offset, femur_offset, tibia_offset]}`, in degrees. If the file doesn't exist, every leg starts with a `[0,0,0]` calibration. It can be edited by hand, but it's usually easier to do it through the `CAL` + `SAVE` gaits from the remote.

### Full Command Reference

Format: `gait:NAME;parameter:value;parameter:value;\n`
(or just `parameter:value;` without changing the gait — updates `RC_data` on the fly)

| Gait | Parameters | What It Does |
|---|---|---|
| `WALK` | `speed, height, raise, spread, turn_angle, dx, dy, rx, ry, rz` | Tripod gait walking. `speed:0` — stand still, holding the pose |
| `STOP` | — | No handler; legs freeze in their current position |
| `CE` | `ce_value` (0-100) | Synchronously folds/unfolds all legs |
| `ROLL` | `speed, roll_range, roll_turn` | Experimental — opens legs one by one around the circle |
| `LEG` | `leg_num, coxa, femur, tibia` | Manual jog of a single leg (absolute angle, clamped to joint limits) |
| `CAL` | `leg_num, coxa, femur, tibia` | Calibration — the same 3 numbers, but as an offset (±20° max); the leg holds at 0/0/0 |
| `ZERO` | `leg_num` | Puts one leg at the servo's true center (1500 μs), ignoring calibration — for mounting the horn |
| `ZEROALL` | — | Same as `ZERO`, but for all 6 legs at once |
| `SAVE` | — | One-shot: writes the current calibration to `calibration.json`, then returns to `CAL` |
| `GETCAL` | `leg_num` | One-shot: sends back `CAL:N:coxa,femur,tibia;` via BLE notify, then returns to `CAL` |
| `WAVE` | `leg_num` | One leg waves (held for the whole cycle), then automatically returns to `WALK` |
| `DANCE` | `dance_id` (0/1/2) | Dances in a loop until the gait is changed; `dance_id` can be changed on the fly |
| — (not a gait) | `J_XY:x\|y` (-100..100) | Joystick input, converted depending on `J_mode` |
| — (not a gait) | `J_mode` (`steer`/`sides`/`shift`/`tilt`) | How to interpret joystick input |
| — (not a gait) | `espi`, `servoi` | Update intervals (ms), rarely need touching |

#### Dances (`dance_id`)

- **0 — Sway**: slow forward/back/side tilts + rotations
- **1 — Bounce**: fast crouch-and-rise + spins

## Usage

Send commands to the board over BLE (Nordic UART Service) or ESP-NOW, using the `gait:NAME;param:value;param:value;\n` format described above. A trailing newline (`\n`) is required over BLE so the parser knows a full command has arrived.

Typical workflow examples:
- **Walking:** `gait:WALK;speed:50;height:20;spread:30;turn_angle:0;\n`
- **Calibrating a leg:** switch to `gait:CAL;leg_num:0;coxa:2;femur:-1;tibia:0;\n`, adjust offsets, then send `gait:SAVE;\n` to persist them to `calibration.json`
- **Reading back calibration:** `gait:GETCAL;leg_num:0;\n` — the board replies over BLE notify with `CAL:0:coxa,femur,tibia;`
- **Joystick control:** set the interpretation mode first with `J_mode:steer;\n`, then stream `J_XY:x|y;\n` values from -100 to 100
- Any parameter can also be updated on its own (`speed:0;\n`) without switching gaits, and it will be applied immediately by the currently active gait

## Notes

This code isn't intended to be perfect — it's not a polished, production-grade reference implementation. If you run into anything unclear, buggy, or if you have questions about how or why something works a certain way, feel free to open an issue or reach out and ask.

---

# Українська

## Про проєкт

Покращена прошивка для гексапода Ukrainian Robotics Kulya 4.0 з покращеною поведінкою робота, конфігурацією та налаштуванням апаратної частини.

## Про Ukrainian Robotics – Kulya 4.0

Ukrainian Robotics – Kulya 4.0 — це платформа гексапода з відкритим кодом, створена для освіти, робототехнічних досліджень та DIY-ентузіастів.

Цей репозиторій не є офіційним проєктом Ukrainian Robotics. Це незалежний софтверний проєкт, що розширює та покращує оригінальну платформу, надаючи альтернативну прошивку, контролери та програмні інструменти.

**Офіційний проєкт:** [Ukrainian Robotics – Kulya 4.0](https://www.ukrainerobotics.com/diy)

## Пов'язані проєкти
| Проєкт                      | Опис                        |
| ---------------------------- | ---------------------------------- |
| [**Kulya Firmware**](https://github.com/T0riU/Kulya_Firmware)           | Прошивка та конфігурація робота   |
| [**Kulya ESP32 Controller**](https://github.com/T0riU/Kulya_Esp32_Controller)   | Прошивка фізичного пульта на ESP32 |
| [**Kulya Python Controller**](https://github.com/T0riU/Kulya_Py_ControllerAndCalibration) | ПК-контролер і калібрування      |
| [**Kulya Android Controller**](https://github.com/T0riU/Kulya_Controller) | Android-контролер          |

## Встановлення

Установка написана "на коліні" (без вилизаного процесу, але робоче).

1. Встановити [Thonny 5.0.0](https://thonny.org) — IDE, яка використовується для прошивки й роботи з платою.
2. Встановити [драйвери USB → UART (VCP)](https://www.silabs.com/software-and-tools/usb-to-uart-bridge-vcp-drivers?tab=downloads).
3. Відкрити Thonny і зайти в **Tools → Options...** *(тут буде картинка куди натискати)*.
4. Підключити ESP32 до комп'ютера, вибрати інтерпретатор **MicroPython (ESP32)**, натиснути **Install or update MicroPython (esptool)** *(картинка меню налаштувань)*.
5. У встановлювачі вибрати target port (має визначитись автоматично), вибрати параметри для вашої конкретної плати ESP32 і встановити прошивку, натиснувши **Install** *(картинка налаштувань установки)*.
6. Щоб зайти у файлову систему плати *(картинка файлової системи)*, використовується такий порядок (це наврядчи "правильно", але надійно працює):
   - Підключити ESP32
   - Після звуку USB-підключення → натиснути кнопку **Stop** (`Ctrl+F2`)
   - `Ctrl+C`
   - `Ctrl+C` ще раз

   `Stop` вмикає софт-ребут, а два `Ctrl+C` зупиняють завантаження прошивки, щоб вона не встигла запуститись до того, як можна буде завантажити файли.
7. Вибрати потрібні файли, утримуючи **Shift** вибрати всі, і натиснути **"Upload to /"** *(картинка вікна завантаження)*.

### Підключення

*(тут буде фото плати)*

Кольори проводів сервоприводу: **коричневий = земля (–)**, **червоний = живлення (+)**, **жовтий = сигнал (S)**.

**RX/TX** на платі сервоконтролера підключаються до **TX2/RX2** на ESP32 — навхрест (RX↔TX), щоб лінія передачі однієї сторони йшла в лінію прийому іншої.

| Канал на платі (число) | Куди підключати | Суглоб |
|---|---|---|
| 1 | Права передня нога (leg0) | Coxa (тазостегновий) |
| 2 | Права передня нога (leg0) | Femur (стегновий) |
| 3 | Права передня нога (leg0) | Tibia (гомілковий) |
| 4, 5 | — не використовуються — | — |
| 6 | Ліва передня нога (leg1) | Coxa |
| 7 | Ліва передня нога (leg1) | Femur |
| 8 | Ліва передня нога (leg1) | Tibia |
| 9 | Ліва середня нога (leg2) | Coxa |
| 10 | Ліва середня нога (leg2) | Femur |
| 11 | Ліва середня нога (leg2) | Tibia |
| 12, 13 | — не використовуються — | — |
| 14 | Ліва задня нога (leg3) | Coxa |
| 15 | Ліва задня нога (leg3) | Femur |
| 16 | Ліва задня нога (leg3) | Tibia |
| 17 | Права задня нога (leg4) | Coxa |
| 18 | Права задня нога (leg4) | Femur |
| 19 | Права задня нога (leg4) | Tibia |
| 20, 21 | — не використовуються — | — |
| 22 | Права середня нога (leg5) | Coxa |
| 23 | Права середня нога (leg5) | Femur |
| 24 | Права середня нога (leg5) | Tibia |

## Як це працює

### Запуск

**`boot.py`** — перше, що виконується при старті плати. Чекає 3 секунди (щоб встигнути перервати завантаження через REPL, якщо треба перепрошити), потім імпортує `run.py`.

**`run.py`** — піднімає всі підсистеми по черзі:
1. `esp_legs_setup` — створює 6 об'єктів `Leg`
2. `esp_ble.ESP32_BLE(...)` — запускає BLE-сервер (реклама, приймач команд)
3. `esp_now_rx` + апаратний таймер — приймач ESP-NOW (фізичний пульт), опитується раз на 50мс
4. `esp_legmover.legmover` — окремий потік (`_thread`), безперервно рахує кути → шле на сервоконтролер по UART
5. `esp_gait_selector.gait_selector()` — головний нескінченний цикл, диспетчер команд

### Спільний стан

**`esp_context.py`** — єдине джерело правди. Словник `RC_data` — усі параметри керування (див. таблицю команд нижче). Його читають/пишуть усі інші модулі. Також тут: `legmover_on` (флаг, чи активний потік руху ніг), `ble_instance` (посилання на BLE-об'єкт, щоб гейти могли слати відповіді), `motion_smooth_rate` (наскільки плавно згладжується рух при `speed:0`).

**`esp_parse_update.py`** — парсер вхідних команд. Розбиває `param:value;...` на пари, кладе в `RC_data`. Окремо обробляє `J_XY` (джойстик) — конвертує `x|y` (-100..100) в `dx/dy/speed/turn_angle` або `rx/ry`, залежно від `J_mode` (`steer` / `sides` / `shift` / `tilt`).

### Зв'язок

**`esp_ble.py`** — BLE-сервер (Nordic UART Service). Приймає команди, **накопичує вхідні шматки в буфер і парсить лише коли зустріне `\n`** (без цього довгі команди різались через ліміт MTU ~20 байт). Клас `ESP32_BLE` сам реєструє себе в `esp_context.ble_instance`, щоб інші модулі могли слати відповіді через `.send(text)`. Світлодіод on-board блимає поки не підключено, горить рівно коли підключено.

**`esp_now_rx.py`** — приймач ESP-NOW, для фізичного пульта (не BLE). Кожен пакет — окрема повна команда (ESP-NOW не ріже на шматки, як BLE).

### Кінематика й рух

**`esp_Leg_class.py`** — клас `Leg`: геометрія (довжини сегментів, ліміти кутів кожного суглоба), піни сервоприводів, `invert` (чи дзеркалити імпульс на суглобі), поточні/цільові/попередні кути. **Не знає** напрямку обходу ніг по колу — кут (`leg_angle`) йому передають ззовні, рахує `esp_legs_setup.py`.

**`esp_inverse_kinematics.py`** — зворотна кінематика. `IK(leg, xyz)` — координати → кути суглобів (з клампом по лімітах ноги). `getSpread_xyz(...)` — параметри стійки (spread/height/tilt/turn) → цільові координати ноги.

**`esp_legmover.py`** — окремий потік. Кожні `espi` мс інтерполює `current_angles` → `target_angles` (ступінчасто, якщо `speed>0`, плавно згладжено якщо `speed:0`), формує рядок команди для ch24-контролера й шле по UART. Тут же — `deg2pulse()` з **жорстким клампом 500-2500 мкс** (ніяке значення калібрування/кута не може вивести серву за безпечний діапазон).

**`esp_legs_setup.py`** — створює 6 об'єктів `Leg`, все з JSON-файлів (див. розділ нижче). Якщо `legs_config.json` не знайдено/пошкоджено — є мінімальний вбудований фолбек (той самий wiring, що робот мав спочатку), щоб плата хоч якось завантажилась, з попередженням в REPL.

### Гейти (`esp_gait_*.py`)

Кожен файл — одна команда `gait:ИМЯ;`, зареєстрована в `esp_gait_selector.py`. Детально — в таблиці команд нижче.

**`esp_gait_selector.py`** — головний диспетчер. Читає `RC_data["gait"]`, викликає відповідну функцію. Обгорнуто в `try/except` — якщо гейт впаде з винятком, диспетчер не вмирає назавжди, а відкочує `gait` в `STOP` і пише причину в REPL.

### JSON-конфіги — що можна міняти без перепрошивки коду

#### `legs_config.json` — залізо (не пишеться кодом автоматично, редагуй руками)

```json
{
  "legs_clockwise": false,
  "0": {"pins": [1, 2, 3],    "invert": [true, false, true]},
  "1": {"pins": [6, 7, 8],    "invert": [true, false, true]},
  "2": {"pins": [9, 10, 11],  "invert": [true, false, true]},
  "3": {"pins": [14, 15, 16], "invert": [true, false, true]},
  "4": {"pins": [17, 18, 19], "invert": [true, false, true]},
  "5": {"pins": [22, 23, 24], "invert": [true, false, true]}
}
```

- **`legs_clockwise`** (`true`/`false`) — напрямок обходу ніг по колу корпуса (за годинниковою чи проти). Одне значення інвертує порядок усіх шести кутів одразу. Перевіряється поворотом при `WALK` — якщо крутить не туди, куди очікуєш, зміни це значення.
- **`"0".."5"`** — кожна нога:
  - `pins` — `[coxa_pin, femur_pin, tibia_pin]`, канали на ch24-контролері
  - `invert` — `[coxa, femur, tibia]`, чи дзеркалити (`3000 - pulse`) імпульс на цьому суглобі цієї ноги. Потрібно, якщо сервоприводи на різних ногах фізично закріплені по-різному.

Читається один раз при старті — зміни вимагають перезавантаження плати.

#### `calibration.json` — калібрування (пишеться автоматично гейтом `SAVE`)

```json
{"0": [0, 0, 0], "1": [0, 0, 0], "2": [0, 0, 0], "3": [0, 0, 0], "4": [0, 0, 0], "5": [0, 0, 0]}
```

`{"leg_num": [coxa_offset, femur_offset, tibia_offset]}`, градуси. Якщо файлу немає — усі ноги стартують з калібруванням `[0,0,0]`. Редагувати руками можна, але зазвичай простіше через гейт `CAL` + `SAVE` з пульта.

### Всі команди

Формат: `gait:ИМЯ;параметр:значення;параметр:значення;\n` (або просто `параметр:значення;` без зміни гейта — оновлює `RC_data` на льоту)

| Гейт | Параметри | Що робить |
|---|---|---|
| `WALK` | `speed, height, raise, spread, turn_angle, dx, dy, rx, ry, rz` | Хода тріподом. `speed:0` — стояти, тримаючи позу |
| `STOP` | — | Немає обробника, ноги застигають у поточному положенні |
| `CE` | `ce_value` (0-100) | Синхронне складання/розкладання всіх ніг |
| `ROLL` | `speed, roll_range, roll_turn` | Експериментальна — по черзі відкриває ноги по колу |
| `LEG` | `leg_num, coxa, femur, tibia` | Ручний джог однієї ноги (абсолютний кут, обрізається лімітами суглоба) |
| `CAL` | `leg_num, coxa, femur, tibia` | Калібрування — ті самі 3 числа як offset (±20° макс), нога тримається в 0/0/0 |
| `ZERO` | `leg_num` | Одна нога в чистий центр серво (1500мкс), ігнорує калібрування — для монтажу рожка |
| `ZEROALL` | — | Те саме, всі 6 ніг одразу |
| `SAVE` | — | Одноразово: пише поточне калібрування в `calibration.json`, повертається в `CAL` |
| `GETCAL` | `leg_num` | Одноразово: шле назад `CAL:N:coxa,femur,tibia;` через BLE notify, повертається в `CAL` |
| `WAVE` | `leg_num` | Одна нога махає (фіксується на весь цикл), потім сам повертається в `WALK` |
| `DANCE` | `dance_id` (0/1/2) | Танцює по колу, поки не зміниш гейт; `dance_id` можна міняти на льоту |
| — (не гейт) | `J_XY:x\|y` (-100..100) | Джойстик, конвертується залежно від `J_mode` |
| — (не гейт) | `J_mode` (`steer`/`sides`/`shift`/`tilt`) | Як інтерпретувати джойстик |
| — (не гейт) | `espi`, `servoi` | Інтервали оновлення (мс), рідко треба чіпати |

#### Танці (`dance_id`)

- **0 — Sway**: повільні нахили вперед/назад/вбік + повороти
- **1 — Bounce**: швидкий присід-підйом + оберти

## Використання

Команди надсилаються на плату через BLE (Nordic UART Service) або ESP-NOW у форматі `gait:ИМЯ;параметр:значення;параметр:значення;\n`, описаному вище. Через BLE обов'язково потрібен символ переносу рядка (`\n`) наприкінці, щоб парсер зрозумів, що команда прийшла повністю.

Типові приклади використання:
- **Ходьба:** `gait:WALK;speed:50;height:20;spread:30;turn_angle:0;\n`
- **Калібрування ноги:** перейти в `gait:CAL;leg_num:0;coxa:2;femur:-1;tibia:0;\n`, підібрати офсети, потім надіслати `gait:SAVE;\n`, щоб зберегти їх у `calibration.json`
- **Зчитування калібрування:** `gait:GETCAL;leg_num:0;\n` — плата відповість через BLE notify рядком `CAL:0:coxa,femur,tibia;`
- **Керування джойстиком:** спочатку задати режим інтерпретації `J_mode:steer;\n`, потім слати значення `J_XY:x|y;\n` від -100 до 100
- Будь-який параметр можна оновити окремо (`speed:0;\n`) без зміни гейта — активний гейт застосує його одразу

## Примітки

Цей код не претендує на ідеальність — це не вилизана, продакшн-грейд реалізація. Якщо щось незрозуміло, знайшли баг, або є питання по тому, як і чому щось працює саме так — не соромтесь відкрити issue або написати й запитати.