# Что изменено (патч поверх kknx-builder-main-11)

Основание: разбор репозитория и скриншотов настроек на устройстве. Ничего из этого не собиралось в CI и не запускалось на телефоне, проверялись скрипты на реальных файлах ядра (`Makefile`, `msm8937.dtsi`, `msm8937-olive.dtsi` из закреплённого коммита) и установщик в песочнице.

## 1. Пресеты (`preset`)
- Новое поле `preset`: `custom` (по умолчанию, поведение прежнее), `baseline`, `stable`, `balanced`, `lab`. Состав: README, раздел `preset`.
- `scripts/resolve_preset.py` разворачивает набор в итоговые значения (`T_*` в `$GITHUB_ENV`), печатает их в лог и в сводку запуска. Итог пишется в `build-info.txt`.
- У `workflow_dispatch` лимит 25 полей, и в `-11` их было ровно 25. Чтобы освободить место, `cc_opt` и `spf` переехали в `experiments` как `inline` и `spf`. Переменные `CC_OPT` и `SPF` в `apply_tweaks.py` по-прежнему работают.

## 2. ccache
- `ccache` ставится из apt, кэш `~/.ccache` восстанавливается и сохраняется через `actions/cache` (ключ с `run_id`, поиск по префиксу), статистика попадает в сводку запуска.
- Подмена компилятора через имя `clang-16`; для `toolchain=neutron` (абсолютный путь к clang) ccache пропускается.
- Ожидание: повторная сборка без смены опций заметно быстрее, при смене опций пересобирается затронутое. Цифр нет: на CI не запускалось.

## 3. Бэкап boot
- `kk_backup_boot` в `anykernel/tools/kknx-extras.sh`, вызывается из `anykernel.sh` сразу после `split_boot`. Копия идёт в `KKNX-backup/boot-<время>.img` в `/sdcard`, а если недоступен, в `/data/media/0` или `/data`. Хранятся три последние. Ошибка бэкапа прошивку не останавливает.
- Проверено в песочнице: все четыре ветки (есть `/sdcard`, нет `/sdcard`, ничего не записывается, нет образа), ротация до трёх, совпадение размера копии.

## 4. ramoops (`experiments=ramoops`)
- `scripts/add_ramoops.py`: узел `ramoops@9ff00000` (1 МБ: console 256 КБ, pmsg 128 КБ, записи по 128 КБ) в `msm8937.dtsi` и `msm8937-olive.dtsi`. Идемпотентен, падает при пересечении с любой `reg` из reserved-memory. Синтаксис узла проверен `dtc`, порядок с LOLZ-портом проверен.
- `apply_tweaks.py` включает `PSTORE`, `PSTORE_CONSOLE`, `PSTORE_PMSG`, `PSTORE_RAM` (проверяется после `olddefconfig`) и добавляет маркер `ramoops` для `verify_image.py`.
- В закреплённом коммите defconfig строк `PSTORE*` нет, хотя ROADMAP утверждал обратное; теперь опции включаются явно.
- Основания для адреса: в этом дереве `drivers/of/platform.c` создаёт устройство для `compatible = "ramoops"` внутри `/reserved-memory`, `fs/pstore/ram.c` читает `reg` и размеры из DT; тот же адрес и размер у mainline-DT Xiaomi msm8953 (tissot, vince). **Адрес на этом устройстве не проверен.**
- `tools/kknx-pstore.sh` забирает журнал после перезагрузки.

## 5. Значения памяти (`runtime_tune`, группа `vm`)
- Добавлены `dirty_background_ratio 5`, `dirty_ratio 20`, `dirty_expire_centisecs 3000`, `dirty_writeback_centisecs 500`, `ksm/run 0`.
- Группа `vm` повторно применяется на `sys.boot_completed=1`.
- Важно: этот сборщик значения `dirty_*` и KSM раньше не ставил. На скриншотах `dirty_ratio 99`, `dirty_background_ratio 50`, 10 минут до сброса на диск и включённый KSM; источник неизвестен (прошивка, ядро по умолчанию или приложение-тюнер). Если приложение применяет свои значения при загрузке позже нас, оно их перекроет.
- Не тронуты: LMK `minfree`, размер zram и `swappiness` (его и так ставит группа `vm`): первые два задаёт не ядро.

## 6. Прочее
- `CRUEL_REF` (пусто = HEAD) позволяет зафиксировать SHA тулчейна; SHA реально использованного коммита пишется в `build-info.txt` (`cruel:`).
- Документация: README, ROADMAP, DETAILS приведены в соответствие.

## Что не сделано сознательно
Бэкпорты (schedutil 4.19, TCP internal pacing, WireGuard compat, F2FS, BFQ-SQ), включение `SECCOMP` и усиление безопасности. Они меняют поведение ядра, а сначала нужны `ramoops` и воспроизводимые замеры (`tools/kknx-test.sh`), иначе виновника не найти. Порядок и причины: в ответе в чате.

## 7. Бэкпорты (второй шаг)
- `experiments=lzorle`: lzo-rle для zram (Linux 5.1); `zram_comp=lzo-rle` включает его сам и делает алгоритмом по умолчанию.
- `experiments=tcppace`: внутренний pacing TCP (Linux 4.13), BBR работает без fq.
- Общий шаг `scripts/apply_backports.py` накладывает `backports/<имя>/<имя>.patch` строго (сначала пробное наложение, при отклонении сборка падает); `apply_tweaks.py` страхует: если значение есть, а патча нет, тоже падает.
- `lab` включает оба. Подробности и что отброшено после проверки: `docs/BACKPORTS.md`. Порядок сборок для сравнения: `docs/MATRIX.md`.
- В `tools/kknx-test.sh zram` добавлен `lzo-rle`.
