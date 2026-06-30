# CSW Telecom RFQ — Handoff

**Проект:** Заполнение RFQ на FLM-услуги по Европе (55 зон)  
**Клиент:** CSW Telecom  
**Статус:** В работе — 4 из 6 колонок заполнены, остался BH-xh (B) и OOH-xh (D) extra hour, плюс финальный перенос в Excel

---

## Goal

Заполнить Excel-файл RFQ (`20260630-CSW-Telecom-RFQ-EuropeMultizone-coverage-matrix.xlsx`) согласованными ставками по всем 55 зонам, 6 колонкам. Рабочий документ ведётся параллельно в MD и HTML.

---

## Файлы

| Файл | Назначение |
|------|-----------|
| `...CSW Telecom\90-Finance\CSW-RFQ-rates-working.md` | Источник данных, все расчёты |
| `...CSW Telecom\90-Finance\CSW-RFQ-rates-working.html` | Читаемое представление, цветовая кодировка по тирам |
| `...CSW Telecom\90-Finance\20260630-CSW-Telecom-RFQ-EuropeMultizone-coverage-matrix.xlsx` | Оригинальный RFQ от клиента (финальная цель) |

Базовый путь: `C:\Users\RHL49\OneDrive - Remotehands 247 B.V\Company Documents - Operations\Operations - Clients\`

---

## Структура колонок RFQ

| Col | Short | Описание |
|-----|-------|---------|
| A | BH-start | Business hours · 4H SLA · Start pack (incl. 2h work/travel) |
| B | BH-xh | Business hours · 4H SLA · Extra hour |
| C | OOH-start | Out of hours · 4H SLA · Start pack (incl. 2h work/travel) |
| D | OOH-xh | Out of hours · 4H SLA · Extra hour |
| E | Day | Day rate · installation · 5 WD notice |
| F | Half-day | ½ Day rate · installation · 5 WD notice |

---

## Согласованные ставки

### Тиры (10 хабов: FRA · MUN · BER · AMS · MIL · STO · BRU · VIE · BRA · LON)

| Tier | Distance | A — BH-start | B — BH-xh | C — OOH-start | D — OOH-xh | E — Day | F — Half-day |
|------|----------|-------------|-----------|--------------|-----------|---------|-------------|
| HQ / No-travel | ≤ 50 km | €2 000 retainer | €95 | €3 000 retainer | €142.50 | €750 | €510 |
| Zone 1 | 51–200 km | €2 350 | €95 | €3 525 | €142.50 | €900 | €660 |
| Zone 2 | 201–400 km | Best effort only | €95 | Best effort only | €142.50 | €1 100 | €860 |
| Zone 3 | 401–530 km | Best effort only | €95 | Best effort only | €142.50 | €1 312.50 | €1 072.50 |
| Zone 4 | 531+ km | Best effort only | €95 | Best effort only | €142.50 | €1 650 | €1 410 |
| Switzerland | — | Best effort only | €95 | Best effort only | €142.50 | per city | per city |

**Формулы:**
- BH-start (точное): `750 + max(0, D−50) × 1.50` €/km
- OOH-start = BH-start × 1.5
- OOH-xh = BH-xh × 1.5 = €142.50
- Day: `750 + max(0, D−50) × 1.50` (тир = округлённое значение)
- Half-day = `510 + (Day tier − 750)` (тот же тревел-сюрчардж)
- Швейцария: база ×2 → Day = `1500 + max(0, D−50) × 1.50`

### Швейцария — индивидуально

| Code | City | E — Day | F — Half-day |
|------|------|---------|-------------|
| LUG | Lugano | €1 545 | €1 065 |
| BLP | Basel | €1 740 | €1 260 |
| LUC | Lucerne | €1 770 | €1 290 |
| ZUR | Zurich | €1 860 | €1 380 |
| GVA | Geneva | €1 875 | €1 395 |

---

## Current State

**Заполнено в рабочем MD/HTML:**
- ✅ Col A (BH-start) — retainer / 2 350 / Best effort по тирам
- ✅ Col B (BH-xh) — €95 везде
- ✅ Col C (OOH-start) — retainer×1.5 / 3 525 / Best effort
- ✅ Col D (OOH-xh) — €142.50 везде
- ✅ Col E (Day) — тиры + Швейцария per-city
- ✅ Col F (Half-day) — тиры + Швейцария per-city

**Не сделано:**
- ❌ Перенос ставок в оригинальный Excel-файл RFQ
- ❌ Уточнить 5 unknown кодов: TIS, REH, LSE, RPK, SIT (запросить у CSW Telecom)

---

## Remaining Work

1. **Unknown зоны** — отправить CSW Telecom запрос: что за локации TIS / REH / LSE / RPK / SIT?
2. **Заполнить Excel** — перенести все согласованные ставки из рабочего MD в оригинальный RFQ-файл (openpyxl или вручную)
3. **Отправить RFQ** — после заполнения отправить клиенту

---

## Next Steps

1. Открыть `CSW-RFQ-rates-working.html` для проверки перед отправкой
2. Написать CSW Telecom про unknown коды
3. Заполнить Excel: `python` + `openpyxl`, читать ставки из MD/HTML, вписать в соответствующие ячейки
4. Отправить готовый RFQ

---

## Notes

- Зоны HEL (Helsinki) и TAA (Tallinn) достигаются паромом через Балтику (~400 и ~430 км)
- DUB (Dublin) — паром из Лондона через Holyhead (~470 км от LON), без LON-хаба был бы €2 175 от BRU
- Швейцария: договорились на двойную базовую ставку (×2), SLA только best effort
- Zone 3 = ×1.75, Zone 4 = ×2.2 (WAW + COP изолированы в Zone 4 как самые дорогие)
