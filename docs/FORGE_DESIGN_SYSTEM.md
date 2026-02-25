# FORGE Design System -- CRUCIBLE

> Telegram Mini App для обучения предпринимательству.
> Метафора: кузница, наковальня, закалка, искры, раскалённый металл.
> "Ты -- металл. Обучение -- огонь. Навыки -- то, что выковано."

---

## 1. ЦВЕТОВАЯ ПАЛИТРА

### Сравнение трёх тем проекта

| Роль | VELVET (Curator) | COSMOS (Partner) | CRUCIBLE (Forge) |
|------|-----------------|-----------------|-----------------|
| Фон 1 (самый тёмный) | `#0C0A09` obsidian | `#050508` void | `#0A0A0A` forge-black |
| Фон 2 | `#1C1917` charcoal | `#0A0A0F` abyss | `#141414` anvil |
| Фон 3 | `#292524` smoke | `#0D0D14` deep-space | `#1E1E1E` soot |
| Фон 4 (карточки) | -- | `#12121C` nebula-dark | `#262626` ingot |
| Акцент primary | `#F59E0B` amber | `#6366F1` indigo | `#FF6B35` spark |
| Акцент soft | `#FCD34D` amber-soft | `#818CF8` glow-soft | `#FF8F5E` ember |
| Акцент deep | `#D97706` amber-deep | `#4F46E5` glow-muted | `#E5501A` molten |
| Текст primary | `#FAF7F2` cream | `#E2E8F0` star-white | `#F0ECE5` ash-white |
| Текст secondary | `#A8A29E` sand | `#94A3B8` star-dim | `#9CA3AF` slag |
| Текст muted | `#78716C` stone | `#64748B` dust | `#6B7280` iron-dust |
| Success | `#10B981` sage | `#818CF8` glow | `#22C55E` tempered |
| Error | `#F87171` | `#F87171` | `#EF4444` quench-fail |
| Warning | `#FBBF24` | `#FBBF24` | `#F59E0B` caution |
| Характер | тёплый, бархатный | холодный, космический | жаркий, индустриальный |

### Полная палитра CRUCIBLE

```
BACKGROUNDS (от тёмного к светлому):
  forge-black   #0A0A0A   -- основной фон body
  anvil         #141414   -- навигация, модалки
  soot          #1E1E1E   -- поверхность карточек
  ingot         #262626   -- ховер карточек, вложенные блоки
  cinder        #333333   -- активные элементы, разделители

ACCENT (оранжево-красная шкала жара):
  spark         #FF6B35   -- primary accent (основная кнопка, индикаторы)
  ember         #FF8F5E   -- мягкий акцент (hover, secondary)
  molten        #E5501A   -- deep accent (pressed, active indicators)
  flame-glow    #FF6B3520 -- glow/shadow (20% opacity)
  white-hot     #FFF0E5   -- максимально нагретый (highlight текст, XP числа)

STEEL (серо-голубая шкала металла):
  steel         #CBD5E1   -- вторичный акцент, рамки, иконки неактивные
  brushed       #94A3B8   -- subtext, captions
  oxidized      #64748B   -- disabled, placeholder
  raw-iron      #475569   -- самые неактивные элементы

TEXT:
  ash-white     #F0ECE5   -- основной текст (чуть теплее чистого белого)
  slag          #9CA3AF   -- вторичный текст
  iron-dust     #6B7280   -- третичный текст / подписи
  dim           #4B5563   -- крайне неактивный текст

STATUS:
  tempered      #22C55E   -- успех (закалён)
  quench-fail   #EF4444   -- ошибка (закалка не удалась)
  caution       #F59E0B   -- предупреждение (перегрев)
  cooling       #3B82F6   -- информация (охлаждение)

TIER COLORS (для скилл-дерева):
  tier-bronze    #CD7F32   -- Tier 1: Бронза
  tier-iron      #71797E   -- Tier 2: Железо
  tier-steel     #71A6D2   -- Tier 3: Сталь
  tier-damascus  #C0A080   -- Tier 4: Дамаск
  tier-mythril   #E8D5FF   -- Tier 5: Мифрил (сияющий)
```

### CSS Custom Properties

```css
:root {
  /* Фоны */
  --forge-black: #0A0A0A;
  --anvil: #141414;
  --soot: #1E1E1E;
  --ingot: #262626;
  --cinder: #333333;

  /* Акценты */
  --spark: #FF6B35;
  --ember: #FF8F5E;
  --molten: #E5501A;
  --flame-glow: rgba(255, 107, 53, 0.12);
  --white-hot: #FFF0E5;

  /* Металл */
  --steel: #CBD5E1;
  --brushed: #94A3B8;
  --oxidized: #64748B;
  --raw-iron: #475569;

  /* Текст */
  --ash-white: #F0ECE5;
  --slag: #9CA3AF;
  --iron-dust: #6B7280;

  /* Статусы */
  --tempered: #22C55E;
  --quench-fail: #EF4444;
  --caution: #F59E0B;
  --cooling: #3B82F6;

  /* Тиры */
  --tier-bronze: #CD7F32;
  --tier-iron: #71797E;
  --tier-steel: #71A6D2;
  --tier-damascus: #C0A080;
  --tier-mythril: #E8D5FF;

  /* Telegram theme mapping */
  --tg-theme-bg-color: var(--forge-black);
  --tg-theme-text-color: var(--ash-white);
  --tg-theme-hint-color: var(--iron-dust);
  --tg-theme-link-color: var(--ember);
  --tg-theme-button-color: var(--spark);
  --tg-theme-button-text-color: #ffffff;
  --tg-theme-secondary-bg-color: var(--anvil);
}
```

---

## 2. ТИПОГРАФИКА

### Шрифт: Inter

Единый шрифт для всех трёх приложений. Уже установлен в проекте.

```
font-family: 'Inter', system-ui, -apple-system, sans-serif;
```

### Шкала размеров

| Токен | Размер | Вес | Высота строки | Применение |
|-------|--------|-----|---------------|------------|
| `display` | 32px (2rem) | 800 (ExtraBold) | 1.1 | Число XP на Home, числа уровней |
| `h1` | 24px (1.5rem) | 700 (Bold) | 1.2 | Заголовки страниц |
| `h2` | 20px (1.25rem) | 700 (Bold) | 1.3 | Заголовки секций |
| `h3` | 16px (1rem) | 600 (SemiBold) | 1.4 | Заголовки карточек |
| `body` | 15px (0.9375rem) | 400 (Regular) | 1.6 | Основной текст |
| `body-sm` | 14px (0.875rem) | 400 (Regular) | 1.5 | Вторичный текст |
| `caption` | 12px (0.75rem) | 500 (Medium) | 1.4 | Подписи, метки |
| `overline` | 11px (0.6875rem) | 600 (SemiBold) | 1.2 | Надписи тиров, uppercase labels |

### Особые стили

```css
/* Числа XP, счётчики -- моноширинный для стабильности */
.font-numeric {
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}

/* Overline labels (TIER, XP, STREAK) */
.overline {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--iron-dust);
}

/* Gradient text -- раскалённый */
.text-gradient-heat {
  background: linear-gradient(90deg, var(--ember), var(--spark), var(--white-hot), var(--spark), var(--ember));
  background-size: 200% 100%;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  animation: heat-shimmer 4s ease-in-out infinite;
}
```

---

## 3. SPACING SYSTEM

Система отступов: **4px base grid**, с основными шагами на 8px.

```
4px    -- 1    (micro gap: между иконкой и текстом в inline)
8px    -- 2    (xs: между элементами в строке)
12px   -- 3    (sm: padding маленьких кнопок)
16px   -- 4    (md: padding карточек, gap между элементами)
20px   -- 5    (lg: padding основных карточек)
24px   -- 6    (xl: gap между секциями)
32px   -- 8    (2xl: margin между блоками)
40px   -- 10   (3xl: top/bottom padding страниц)
48px   -- 12   (4xl: большие отступы)
```

### Стандартные паттерны отступов

| Элемент | Padding / Margin |
|---------|-----------------|
| Страница (page padding) | `px-4 pt-2 pb-24` (16px sides, 8px top, 96px bottom для навбара) |
| Секция gap | `space-y-6` (24px) |
| Карточка padding | `p-4` или `p-5` (16-20px) |
| Элементы внутри карточки gap | `space-y-3` (12px) |
| Inline items gap | `gap-2` (8px) |
| Кнопка padding | `px-5 py-2.5` (20px / 10px) |
| Навбар высота | `h-16` (64px) + safe area |

---

## 4. BORDER RADIUS

```
none    -- 0px    (почти не используем)
sm      -- 6px    (маленькие чипы, бейджи)
DEFAULT -- 8px    (кнопки маленькие)
md      -- 10px   (инпуты)
lg      -- 12px   (карточки средние)
xl      -- 16px   (большие карточки)
2xl     -- 20px   (модалки, bottom sheet)
full    -- 9999px (таблетки, аватарки, прогресс-бары)
```

Стратегия: кузнечная тема -- чуть более angular чем VELVET/COSMOS. Карточки с `rounded-xl` (16px) вместо `rounded-2xl` (20px), кнопки с `rounded-lg` (12px). Это создаёт ощущение "выкованных" форм -- не острых, но и не чрезмерно мягких.

---

## 5. ТЕНИ И СВЕЧЕНИЯ (FORGE THEME)

### Box Shadows

```css
/* Уровни теней */
--shadow-card: 0 4px 24px rgba(0, 0, 0, 0.5),
               inset 0 1px 0 rgba(255, 255, 255, 0.03);

--shadow-card-hover: 0 8px 32px rgba(0, 0, 0, 0.6),
                     0 0 0 1px rgba(255, 107, 53, 0.1);

--shadow-elevated: 0 12px 40px rgba(0, 0, 0, 0.7),
                   0 0 0 1px rgba(255, 107, 53, 0.08);

/* Свечения в стиле кузницы */
--glow-spark-sm: 0 0 10px rgba(255, 107, 53, 0.2);
--glow-spark-md: 0 0 20px rgba(255, 107, 53, 0.3);
--glow-spark-lg: 0 0 40px rgba(255, 107, 53, 0.4);

/* Glow для прогресс-баров и активных элементов */
--glow-ember: 0 0 8px rgba(255, 107, 53, 0.4),
              0 0 20px rgba(255, 107, 53, 0.2);

/* Glow для tier-mythril (особенный) */
--glow-mythril: 0 0 15px rgba(232, 213, 255, 0.3),
                0 0 40px rgba(232, 213, 255, 0.15);

/* Внутреннее свечение карточки при hover (жар изнутри) */
--inner-heat: inset 0 -1px 30px rgba(255, 107, 53, 0.04);
```

### Heat Gradient (фоновый градиент для акцентных карточек)

```css
.card-heated {
  background: linear-gradient(
    135deg,
    rgba(255, 107, 53, 0.04) 0%,
    var(--soot) 40%,
    var(--soot) 100%
  );
}
```

---

## 6. СПИСОК КОМПОНЕНТОВ

### Атомарные (Atoms)

| Компонент | Описание |
|-----------|----------|
| `Button` | primary / secondary / ghost / danger, sizes: sm/md/lg |
| `Badge` | статус-бейдж (tier, streak, status) |
| `Icon` | обёртка для lucide-react иконок |
| `Chip` | таблетка с текстом (tags, categories) |
| `Avatar` | аватар пользователя (круг) |
| `Divider` | горизонтальный разделитель |
| `Skeleton` | шиммер-скелетон для загрузки |
| `Dot` | цветная точка статуса |

### Молекулярные (Molecules)

| Компонент | Описание |
|-----------|----------|
| `XPProgressBar` | прогресс-бар с анимацией, ember glow, числа XP |
| `StreakCounter` | счётчик дней подряд (огненный значок + число) |
| `TierBadge` | бейдж тира (Bronze/Iron/Steel/Damascus/Mythril) |
| `LessonCard` | карточка урока (превью: иконка, название, длительность, статус) |
| `ExperimentCard` | карточка эксперимента (статус: active/completed/abandoned) |
| `AchievementCard` | карточка достижения (locked/unlocked с анимацией) |
| `StatBlock` | блок статистики (число + подпись) |
| `ActionButton` | кнопка быстрого действия (иконка + текст, на Home) |
| `PathNode` | узел скилл-дерева (locked/available/completed) |
| `CalendarGrid` | сетка дней для heatmap активности |
| `EmberField` | фоновый компонент с плавающими искрами |
| `HeatOverlay` | noise/grain overlay (аналог GrainOverlay) |

### Организмы (Organisms)

| Компонент | Описание |
|-----------|----------|
| `Navigation` | нижний таб-бар (5 табов) |
| `Header` | шапка страницы (заголовок + опциональная кнопка назад) |
| `SkillTree` | визуализация дерева навыков (3 пути x 5 тиров) |
| `LessonReader` | рендерер контента урока (markdown + action block) |
| `ExperimentTimeline` | лента экспериментов (вертикальная) |
| `AchievementGrid` | сетка достижений |
| `ProfileStats` | блок статистики профиля |
| `QuickActions` | секция быстрых действий на Home |
| `TodayLesson` | главная карточка "Урок дня" |
| `BottomSheet` | модальный bottom sheet (для деталей) |

---

## 7. НАВИГАЦИЯ

### Нижний таб-бар: 5 табов

```
[ Home ]  [ Path ]  [ Lesson ]  [ Lab ]  [ Profile ]
   /\        /\        /\         /\         /\
  Flame    Route     BookOpen   Flask    UserCircle
```

| Таб | Иконка (lucide-react) | Label | Путь |
|-----|----------------------|-------|------|
| Home | `Flame` | Горн | `/` |
| Path | `Route` | Путь | `/path` |
| Lesson | `BookOpen` | Урок | `/lesson` |
| Lab | `Beaker` или `FlaskConical` | Лаб | `/lab` |
| Profile | `UserCircle` | Я | `/profile` |

### Визуал навбара

```
Высота: 64px + env(safe-area-inset-bottom)
Фон: rgba(20, 20, 20, 0.85) + backdrop-filter: blur(20px)
Бордер сверху: 1px solid rgba(255, 107, 53, 0.08)

Неактивный таб:
  Иконка: 22px, цвет var(--iron-dust) #6B7280
  Текст: 11px, font-weight 500, var(--iron-dust)

Активный таб:
  Иконка: 22px, цвет var(--spark) #FF6B35, scale(1.1) через framer-motion
  Текст: 11px, font-weight 600, var(--spark)
  Индикатор: layoutId="nav-indicator"
    Полоса 32px x 2px, rounded-full
    background: linear-gradient(90deg, transparent, var(--spark), transparent)
    Позиция: bottom 0
    Анимация: SPRING_SNAPPY { stiffness: 300, damping: 30 }
```

### Navigation Flow

```
Home -----> Lesson (нажал "Продолжить урок")
Home -----> Path (нажал "Скилл-дерево")
Home -----> Lab (нажал "Мои эксперименты")

Path -----> Lesson (нажал на конкретный узел дерева)
Path -----> (TG BackButton) --> Home

Lesson ---> (TG BackButton) --> Path или Home (откуда пришёл)
Lesson ---> (Action completed) --> Home (с анимацией XP)

Lab ------> ExperimentDetail (bottom sheet)
Lab ------> (TG BackButton) --> Home

Profile --> AchievementDetail (bottom sheet)
Profile --> (TG BackButton) --> Home
```

### Telegram BackButton

```typescript
// При входе на "вложенную" страницу (Lesson из Path):
useEffect(() => {
  showBackButton(() => {
    navigateBack()
    hideBackButton()
  })
  return () => hideBackButton()
}, [])
```

---

## 8. СТРАНИЦЫ -- ДЕТАЛЬНЫЕ ВАЙРФРЕЙМЫ

---

### 8.1 HOME (Горн)

Главный экран. Информационная панель + быстрые действия.

```
+------------------------------------------+
|  [safe-area-top]                         |
|                                          |
|  "Горн"                          [avatar]|
|  Привет, Данил                           |
|                                          |
+------ TODAY'S LESSON (Hero card) --------+
|                                          |
|  [BookOpen icon]        TIER 2 / ЖЕЛЕЗО  |
|                                          |
|  Как валидировать идею                   |
|  за 48 часов                             |
|                                          |
|  15 мин  |  3/7 пройдено                 |
|                                          |
|  [ =====>---------  42%  ]   XP bar     |
|                                          |
|  [  Продолжить  -->  ]                   |
|                                          |
+------------------------------------------+
|                                          |
|  STATS ROW (3 блока в ряд)              |
|  +----------+----------+-----------+     |
|  |  [fire]  | [zap]    | [target]  |     |
|  |  12      | 2,450    | 8/30     |     |
|  |  дней    | XP       | уроков   |     |
|  +----------+----------+-----------+     |
|                                          |
+------------------------------------------+
|                                          |
|  БЫСТРЫЕ ДЕЙСТВИЯ                       |
|                                          |
|  [Route] Скилл-дерево    [>]            |
|  [Flask] Мои эксперименты [>]           |
|  [Trophy] Достижения      [>]           |
|                                          |
+------------------------------------------+
|  ПОСЛЕДНИЕ ДОСТИЖЕНИЯ                    |
|                                          |
|  [locked] [locked] [unlocked] [unlocked] |
|  Огнеупор  Кузнец   Первая    7 дней    |
|                     искра    подряд     |
+------------------------------------------+
|                                          |
|  [nav: Home | Path | Lesson | Lab | Me ] |
+------------------------------------------+
```

#### Детали компонентов Home:

**Hero Card (Today's Lesson):**
- Фон: `var(--soot)` с gradient overlay `linear-gradient(135deg, rgba(255,107,53,0.06) 0%, transparent 60%)`
- border: `1px solid rgba(255,107,53,0.12)`
- border-radius: `16px`
- padding: `20px`
- Кнопка "Продолжить": `btn-primary` с иконкой `ArrowRight` (16px)
- Tier badge в правом верхнем углу: `TierBadge` компонент

**Stats Row:**
- 3 карточки `StatBlock` в `flex` с `gap-3`
- Каждая: `bg-soot`, `rounded-xl`, `p-3`, `text-center`
- Иконка: 16px, цвет `var(--spark)`
- Число: `display` стиль (20px, font-weight 800, `font-numeric`)
- Подпись: `caption` стиль (12px, `var(--slag)`)

**Quick Actions:**
- Список `ActionButton`: `flex items-center justify-between`
- Левая часть: иконка (20px, `var(--spark)`) + текст (15px, `var(--ash-white)`)
- Правая часть: `ChevronRight` (16px, `var(--iron-dust)`)
- Разделитель: `1px solid var(--ingot)` между элементами
- При нажатии: `scale(0.98)` + haptic `light`

**Recent Achievements:**
- Горизонтальный скролл, `overflow-x-auto`, `scrollbar-hidden`
- Каждая: 64px x 64px, `rounded-xl`
- Locked: `bg-ingot`, иконка `Lock` (20px, `var(--raw-iron)`), grayscale
- Unlocked: `bg-soot`, иконка достижения, цвет тира, `glow-spark-sm`

---

### 8.2 PATH (Скилл-дерево)

Визуализация трёх путей обучения с 5 тирами в каждом.

```
+------------------------------------------+
|  [safe-area-top]                         |
|                                          |
|  "Путь мастера"                          |
|                                          |
+-- PATH SELECTOR (3 вкладки) -------------+
|                                          |
|  [ Идеи ]  [ Запуск ]  [ Рост ]         |
|   active     ---         ---             |
|  ====== sliding indicator =====          |
|                                          |
+-- SKILL TREE (vertical scroll) ----------+
|                                          |
|  TIER 5 -- МИФРИЛ ................       |
|                    [locked]              |
|                    [locked]              |
|                       |                  |
|  TIER 4 -- ДАМАСК .............          |
|                    [locked]              |
|                    [locked]              |
|                       |                  |
|  TIER 3 -- СТАЛЬ ..............          |
|                   [available]            |
|                    [locked]              |
|                       |                  |
|  TIER 2 -- ЖЕЛЕЗО .............          |
|                  [completed]             |
|                  [completed]             |
|                       |                  |
|  TIER 1 -- БРОНЗА .............          |
|                  [completed]             |
|                  [completed]             |
|                  [completed]             |
|                                          |
+------------------------------------------+
```

#### Детали компонентов Path:

**Path Selector (3 вкладки):**
- Контейнер: `bg-anvil`, `rounded-full`, `p-1`, `flex`
- Каждая вкладка: `flex-1`, `py-2`, `text-center`, `rounded-full`
- Активная: `bg-soot`, `text-ash-white`, font-weight 600
- Неактивная: `text-iron-dust`
- Sliding background: `layoutId="path-selector"`, `SPRING_SNAPPY`
- При переключении: haptic `selection`

**3 пути:**
| Путь | Название | Описание | Иконка |
|------|----------|----------|--------|
| ideas | Идеи | Генерация и валидация идей | `Lightbulb` |
| launch | Запуск | MVP, первые продажи | `Rocket` |
| growth | Рост | Масштабирование, команда | `TrendingUp` |

**Skill Tree Layout:**
- Вертикальный скролл снизу вверх (Tier 1 внизу, Tier 5 вверху)
- Реальная реализация: `flex flex-col-reverse` (чтобы Tier 1 был внизу)
- Между тирами: вертикальная линия-соединитель
  - Completed: `2px solid var(--spark)`, animated glow
  - Locked: `2px dashed var(--cinder)`
- Каждый tier имеет label слева: "TIER 1 -- БРОНЗА" в `overline` стиле

**PathNode (узел дерева):**

3 состояния:

```
COMPLETED:
  Круг 56px, border 2px solid var(--spark)
  Фон: radial-gradient(circle, rgba(255,107,53,0.15) 0%, var(--soot) 70%)
  Иконка: Check (24px), цвет var(--spark)
  Glow: var(--glow-spark-sm)
  Название урока: text-ash-white, 13px, под кружком

AVAILABLE (текущий):
  Круг 56px, border 2px solid var(--spark), пульсирующий
  Фон: var(--soot)
  Иконка урока (24px), цвет var(--spark)
  animation: breathe 3s ease-in-out infinite (пульсация)
  Glow: var(--glow-spark-md), animate-glow-pulse
  Название: text-ash-white, 13px, font-weight 600

LOCKED:
  Круг 56px, border 1px solid var(--cinder)
  Фон: var(--ingot)
  Иконка: Lock (20px), цвет var(--raw-iron)
  Без свечения
  Название: text-iron-dust, 13px
```

**Tier Divider:**
```
TIER N -- НАЗВАНИЕ
Полоса: 100% ширины, высота 1px
Цвет полосы: gradient от transparent через tier-color к transparent
Текст тира слева: overline стиль, цвет tier-color
```

---

### 8.3 LESSON (Урок)

Чтение урока. Полноэкранный reader.

```
+------------------------------------------+
|  [TG BackButton]                         |
|                                          |
|  TIER 2 / ЖЕЛЕЗО       Урок 3 из 7      |
|                                          |
|  Как валидировать идею                   |
|  за 48 часов                             |
|                                          |
|  [====>----------]  42%    ~12 мин       |
|                                          |
+------------------------------------------+
|                                          |
|  ## Зачем валидировать?                  |
|                                          |
|  Большинство стартапов проваливаются     |
|  не потому что плохая идея, а потому     |
|  что...                                  |
|                                          |
|  > "Не строй то, что никому не нужно."  |
|  > -- YC Motto                           |
|                                          |
|  ### Шаг 1: Описать проблему            |
|                                          |
|  Заполни шаблон:                         |
|  - Кто? ___                              |
|  - Что болит? ___                        |
|  - Как решают сейчас? ___                |
|                                          |
|  ### Шаг 2: Поговорить с 5 людьми       |
|  ...                                     |
|                                          |
+-- ACTION BLOCK (sticky bottom) ----------+
|                                          |
|  Задание:                                |
|  Опиши проблему для своей идеи          |
|                                          |
|  [  Отправить ответ  ]                  |
|                                          |
|  или                                     |
|                                          |
|  [  Пометить как выполнено  ]           |
|                                          |
+------------------------------------------+
```

#### Детали компонентов Lesson:

**Lesson Header:**
- Фиксированная шапка при скролле: `position: sticky, top: 0, z-index: 20`
- Фон: `var(--forge-black)` с `backdrop-filter: blur(12px)` + opacity 0.95
- Border-bottom: `1px solid rgba(255,107,53,0.06)`
- TierBadge слева, "Урок N из M" справа (caption, var(--slag))
- Название: h2 (20px, bold)
- Progress bar: высота 3px, `rounded-full`
  - Track: `var(--ingot)`
  - Fill: `linear-gradient(90deg, var(--molten), var(--spark), var(--ember))`
  - Glow на конце: `box-shadow: 0 0 8px var(--spark)`

**Lesson Content (Markdown Renderer):**
- Padding: `px-4 py-6`
- `h2`: 18px, bold, `var(--ash-white)`, margin-top 28px, margin-bottom 12px
- `h3`: 16px, semibold, `var(--ash-white)`, margin-top 20px, margin-bottom 8px
- `p`: 15px, regular, `var(--slag)`, line-height 1.7, margin-bottom 16px
- `blockquote`: border-left 3px solid `var(--spark)`, padding-left 16px, `var(--slag)`, italic, bg: `rgba(255,107,53,0.03)`
- `code`: `bg-ingot`, `px-1.5 py-0.5`, `rounded`, `text-ember`, font-size 14px
- `ul/ol`: padding-left 20px, marker color `var(--spark)`, gap 8px
- `strong`: `var(--ash-white)`, font-weight 600
- Links: `var(--spark)`, underline на hover

**Action Block:**
- Position: sticky bottom или fixed bottom (над навбаром)
- Фон: `var(--anvil)` с `backdrop-filter: blur(16px)`
- Border-top: `1px solid rgba(255,107,53,0.1)`
- Border-radius: `20px 20px 0 0`
- Padding: `20px 16px` + safe-area-bottom
- Shadow: `0 -4px 20px rgba(0,0,0,0.3)`
- Кнопка "Отправить ответ": `btn-primary`, full width
- Кнопка "Пометить как выполнено": `btn-secondary`, full width, margin-top 8px
- textarea (если нужен ответ): `input` стиль, min-height 80px, max-height 160px

**Completion Animation:**
При нажатии "Выполнено":
1. Кнопка: `scale(0.95)` -> `scale(1.05)` -> `scale(1)` (0.3s)
2. Haptic: `success`
3. Иконка Check появляется в центре экрана (scale 0 -> 1.2 -> 1, spring)
4. Круг из искр (canvas-confetti, orange/yellow particles)
5. XP gain toast сверху: "+50 XP" (slide down, hold 2s, slide up)
6. Через 1.5s: автопереход на следующий урок или обратно на Path

---

### 8.4 LAB (Лаборатория экспериментов)

Трекер "1000 стартапов" -- список экспериментов пользователя.

```
+------------------------------------------+
|  [safe-area-top]                         |
|                                          |
|  "Лаборатория"                           |
|                                          |
|  Твоя кузница экспериментов.             |
|  Запускай, тестируй, учись.              |
|                                          |
|  OVERALL STATS                           |
|  +--------+--------+--------+            |
|  |  5     |  2     |  1     |            |
|  | всего  | активн | заверш |            |
|  +--------+--------+--------+            |
|                                          |
+-- FILTER CHIPS --------------------------+
|                                          |
|  [ Все ]  [ Активные ]  [ Завершённые ] |
|                                          |
+-- EXPERIMENT CARDS (vertical list) ------+
|                                          |
|  +--------------------------------------+|
|  | [active dot]  Телеграм-бот для кафе  ||
|  | Гипотеза: Кафе нужен бот для...      ||
|  | День 12 / 30    Метрика: 3 клиента   ||
|  | [====>------]  40%                    ||
|  +--------------------------------------+|
|                                          |
|  +--------------------------------------+|
|  | [completed]  Лендинг для курса       ||
|  | Результат: 23 лида за 14 дней        ||
|  | Вывод: Сработало! Масштабировать.    ||
|  +--------------------------------------+|
|                                          |
|  +--------------------------------------+|
|  | [abandoned]  NFT-маркетплейс         ||
|  | Причина: Нет product-market fit      ||
|  +--------------------------------------+|
|                                          |
+-- FAB (Floating Action Button) ----------+
|                              [+ Новый]   |
|                                          |
+------------------------------------------+
```

#### Детали компонентов Lab:

**Overall Stats:**
- Такие же `StatBlock` как на Home, но 3 в ряд
- Числа: active = `var(--spark)`, completed = `var(--tempered)`, abandoned = `var(--slag)`

**Filter Chips:**
- Горизонтальный скролл
- `Chip` компонент: `bg-ingot`, `text-slag`, `rounded-full`, `px-4 py-2`
- Активный: `bg-spark`, `text-forge-black`, font-weight 600
- Переключение: haptic `selection`, layoutId для скольжения фона

**ExperimentCard:**

3 состояния:

```
ACTIVE:
  bg-soot, border 1px solid rgba(255,107,53,0.15)
  Статус-точка: 8px круг, var(--spark), animate-breathe
  Название: h3, var(--ash-white)
  Гипотеза: body-sm, var(--slag), line-clamp-2
  Прогресс: "День N / M" caption, var(--iron-dust)
  Метрика: caption, var(--ember)
  Progress bar: 3px, var(--spark) fill
  При тапе: открыть BottomSheet с деталями

COMPLETED:
  bg-soot, border 1px solid rgba(34,197,94,0.15)
  Статус-точка: 8px круг, var(--tempered)
  Иконка: CheckCircle2 перед названием
  Название: h3, var(--ash-white)
  Результат: body-sm, var(--tempered)
  Вывод: body-sm, var(--slag), italic
  Нет progress bar

ABANDONED:
  bg-soot, border 1px solid rgba(75,85,99,0.15)
  opacity: 0.7
  Статус-точка: 8px круг, var(--raw-iron)
  Иконка: XCircle перед названием
  Название: h3, var(--slag), line-through
  Причина: body-sm, var(--iron-dust)
```

**FAB (Floating Action Button):**
- Position: `fixed`, bottom: `calc(80px + env(safe-area-inset-bottom))`
- right: `16px`
- Размер: `56px` круг
- Фон: `linear-gradient(135deg, var(--spark), var(--molten))`
- Shadow: `0 4px 16px rgba(255,107,53,0.4)`
- Иконка: `Plus` (24px, white)
- При нажатии: `scale(0.9)` -> `scale(1.1)` -> `scale(1)`, haptic `medium`
- Открывает BottomSheet с формой нового эксперимента

---

### 8.5 PROFILE (Профиль)

Статистика, достижения, heatmap активности.

```
+------------------------------------------+
|  [safe-area-top]                         |
|                                          |
|  PROFILE HEADER                          |
|  +--------------------------------------+|
|  |  [avatar 64px]                       ||
|  |  Данил Мафиозников                   ||
|  |                                      ||
|  |  TIER 2: ЖЕЛЕЗО                      ||
|  |  [TierBadge]                         ||
|  |                                      ||
|  |  [=====>---------]  2,450 / 5,000 XP ||
|  +--------------------------------------+|
|                                          |
+-- STAT GRID (2x2) ----------------------+
|                                          |
|  +---------+---------+                   |
|  | 30      | 12      |                   |
|  | уроков  | дней    |                   |
|  | пройдено| streak  |                   |
|  +---------+---------+                   |
|  | 5       | 2,450   |                   |
|  | экспери-| XP      |                   |
|  | ментов  | всего   |                   |
|  +---------+---------+                   |
|                                          |
+-- ACTIVITY CALENDAR --------------------+
|                                          |
|  Февраль 2026                            |
|                                          |
|  Пн Вт Ср Чт Пт Сб Вс                  |
|  [.][.][#][#][.][.][.]                   |
|  [#][#][.][#][#][.][.]                   |
|  [.][#][#][#][.][.][.]                   |
|  [.][.][.][=СЕГОДНЯ=]                    |
|                                          |
|  . = нет активности (var(--ingot))       |
|  # = была активность (var(--spark) @15%) |
|  TODAY = пульсирующий (glow)             |
|                                          |
+-- ACHIEVEMENTS --------------------------+
|                                          |
|  "Достижения"              12 / 30       |
|                                          |
|  [unlocked] [unlocked] [locked] [locked] |
|  Первая     7 дней    Кузнец   Мастер   |
|  искра      подряд                       |
|                                          |
|  [unlocked] [locked]  [locked] [locked]  |
|  5 экспер.  10 экс.   ...      ...      |
|                                          |
+------------------------------------------+
```

#### Детали компонентов Profile:

**Profile Header:**
- Фон карточки: gradient `linear-gradient(135deg, rgba(255,107,53,0.04) 0%, var(--soot) 50%)`
- Avatar: 64px, `rounded-full`, border `2px solid var(--spark)`
- Имя: h1 (24px, bold, `var(--ash-white)`)
- Tier: `TierBadge` компонент + `overline` текст
- XP bar: высота 6px, `rounded-full`
  - Track: `var(--ingot)`
  - Fill: `linear-gradient(90deg, var(--molten), var(--spark))`
  - Текст: "2,450 / 5,000 XP" caption, `var(--slag)`

**Stat Grid (2x2):**
- CSS Grid: `grid-cols-2`, `gap-3`
- Каждая ячейка: `bg-soot`, `rounded-xl`, `p-4`
- Число: 24px, bold, `font-numeric`
  - Streak число: `var(--spark)` (оранжевый, потому что огонь)
  - XP число: `var(--white-hot)`
  - Остальные: `var(--ash-white)`
- Подпись: caption, `var(--slag)`

**Activity Calendar (Heatmap):**
- Контейнер: `bg-soot`, `rounded-xl`, `p-4`
- Заголовок: h3 + навигация месяцев (ChevronLeft / ChevronRight)
- Grid: `grid-cols-7`, `gap-1`
- Каждый день: квадрат 32px x 32px, `rounded-md`
- 4 уровня интенсивности:
  - 0 активностей: `var(--ingot)` (тёмный)
  - 1-2 активности: `rgba(255,107,53,0.15)`
  - 3-4 активности: `rgba(255,107,53,0.35)`
  - 5+ активностей: `rgba(255,107,53,0.6)`, `glow-spark-sm`
- Сегодня: border `1px solid var(--spark)`, `animate-breathe`

**Achievements Grid:**
- Grid: `grid-cols-4`, `gap-3`
- Каждое: 72px x 80px, `flex flex-col items-center`
- Иконка-круг: 48px, `rounded-xl`

```
UNLOCKED:
  bg: radial-gradient(circle, rgba(tier-color, 0.15) 0%, var(--soot) 70%)
  border: 1px solid rgba(tier-color, 0.3)
  Иконка: achievement icon, 24px, цвет tier
  Название: caption (11px), var(--ash-white), text-center
  Анимация при первом показе: scale 0 -> 1.1 -> 1 + haptic success

LOCKED:
  bg: var(--ingot)
  border: 1px solid var(--cinder)
  Иконка: Lock, 20px, var(--raw-iron)
  Название: caption, var(--iron-dust)
  opacity: 0.5
  filter: grayscale(100%)
```

---

## 9. СИСТЕМА АНИМАЦИЙ И "JUICE"

### 9.1 Spring Presets (framer-motion)

```typescript
// Быстрый, упругий -- для навигации, табов, тоглов
export const SPRING_SNAPPY = { type: 'spring', stiffness: 300, damping: 30 }

// Пружинистый -- для появления элементов, celebration
export const SPRING_BOUNCY = { type: 'spring', stiffness: 200, damping: 15 }

// Плавный -- для переходов страниц, фейдов
export const SPRING_GENTLE = { type: 'spring', stiffness: 100, damping: 20 }

// Тяжёлый -- для "кузнечных" эффектов (удар молота)
export const SPRING_ANVIL = { type: 'spring', stiffness: 400, damping: 25, mass: 1.5 }
```

### 9.2 Page Transitions

```typescript
// AnimatePresence mode="wait" в App.tsx
const pageVariants = {
  initial: { opacity: 0, y: 16, scale: 0.98 },
  animate: { opacity: 1, y: 0, scale: 1 },
  exit: { opacity: 0, y: -8, scale: 0.99 },
}

// Transition: SPRING_GENTLE
// Направление: всегда slide up при входе, fade при выходе
```

### 9.3 Stagger Animations (списки)

```typescript
export const staggerContainer = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.05 },  // 50ms между элементами
  },
}

export const staggerItem = {
  hidden: { opacity: 0, y: 16, scale: 0.97 },
  show: {
    opacity: 1, y: 0, scale: 1,
    transition: SPRING_SNAPPY,
  },
}
```

### 9.4 Micro-Interactions

**Button Press:**
```typescript
<motion.button
  whileTap={{ scale: 0.96 }}
  transition={SPRING_SNAPPY}
  onClick={() => haptic('light')}
>
```

**Card Tap:**
```typescript
<motion.div
  whileTap={{ scale: 0.98 }}
  transition={SPRING_SNAPPY}
>
```

**Toggle/Switch:**
```typescript
// Кружок скользит влево-вправо
<motion.div
  layout
  transition={SPRING_SNAPPY}
/>
```

### 9.5 Achievement Unlock Animation

Последовательность при разблокировке достижения:

```
Frame 0ms:    Overlay затемняет экран (opacity 0 -> 0.7, 200ms)
Frame 200ms:  Достижение появляется в центре (scale 0 -> 1.3 -> 1, SPRING_BOUNCY)
Frame 300ms:  Haptic: 'success'
Frame 400ms:  Название появляется снизу (y: 20 -> 0, opacity 0 -> 1)
Frame 500ms:  Описание появляется (y: 10 -> 0, opacity 0 -> 1)
Frame 600ms:  Искры canvas-confetti (particle count: 60, colors: ['#FF6B35', '#FF8F5E', '#FFF0E5'])
Frame 2500ms: Автозакрытие (opacity -> 0, scale 1 -> 0.9, 300ms)
```

Конфигурация confetti:
```typescript
confetti({
  particleCount: 60,
  spread: 80,
  origin: { y: 0.5, x: 0.5 },
  colors: ['#FF6B35', '#FF8F5E', '#FFF0E5', '#E5501A'],
  gravity: 1.2,
  ticks: 150,
  shapes: ['circle'],  // круглые "искры", не квадраты
  scalar: 0.8,
})
```

### 9.6 Streak Celebration

При входе в приложение, если streak продлён:

```
Frame 0ms:    StreakCounter на Home пульсирует (scale 1 -> 1.2 -> 1, SPRING_BOUNCY)
Frame 100ms:  Haptic: 'success'
Frame 200ms:  Число streak анимируется (AnimatedNumber: old -> new)
Frame 300ms:  Огненный значок делает "bounce" (rotate -10 -> 10 -> 0)
Frame 400ms:  Текст "12 дней подряд!" появляется снизу
Frame 500ms:  Если milestone (7, 14, 30, 60, 100):
              - Дополнительный confetti
              - Toast: "Достижение: 14 дней подряд!"
```

### 9.7 XP Gain Animation

При получении XP (после завершения урока, эксперимента):

```
1. Toast сверху экрана:
   - Slide down: y: -40 -> 0, opacity 0 -> 1 (SPRING_BOUNCY)
   - Содержимое: "[Zap icon] +50 XP"
   - Фон: rgba(255,107,53,0.15), border: 1px solid rgba(255,107,53,0.3)
   - Текст: var(--white-hot), font-weight 700
   - Hold: 2000ms
   - Slide up: y: 0 -> -40, opacity 1 -> 0 (300ms ease)

2. XP Bar на Home (если видим):
   - Ширина fill анимируется: old% -> new% (spring, duration 800ms)
   - Glow на конце fill пульсирует ярче (0.6s)
   - Число XP: AnimatedNumber (old -> new)

3. Если level up (переход на новый tier):
   - Полноэкранная анимация TierUp (см. ниже)
```

### 9.8 Tier Up (Level Up) Animation

Полноэкранная celebration:

```
Frame 0ms:    Overlay: forge-black, opacity 0 -> 1
Frame 300ms:  Наковальня (emoji или SVG) появляется в центре, scale 0 -> 1 (SPRING_ANVIL)
Frame 600ms:  Молот ударяет сверху (y: -200 -> 0, SPRING_ANVIL)
Frame 700ms:  Haptic: 'heavy'
Frame 800ms:  Вспышка: круг из центра расширяется (scale 0 -> 3), цвет tier-а, opacity 1 -> 0
Frame 1000ms: Новый TierBadge появляется (scale 0 -> 1.2 -> 1, SPRING_BOUNCY)
Frame 1200ms: Текст "TIER 3: СТАЛЬ" (fadeInUp)
Frame 1400ms: Текст "Ты продвигаешься!" (fadeInUp)
Frame 1600ms: Confetti с цветами tier-а
Frame 3000ms: Кнопка "Продолжить" (fadeIn)
```

### 9.9 Ember Field (фоновые искры)

Аналог AmbientGlow (VELVET) и Stars (COSMOS), но в стиле кузницы.

```typescript
// EmberField.tsx — плавающие искры, поднимающиеся снизу вверх

interface Ember {
  id: number
  x: number        // 0-100% горизонтально
  startY: number   // 80-100% (начинают снизу)
  size: number     // 2-5px
  opacity: number  // 0.1-0.4
  duration: number // 8-20s (время подъёма до верха)
  sway: number     // -30px to 30px (горизонтальное покачивание)
  delay: number    // 0-10s (задержка старта)
}

// Генерируем 30-40 искр
// Каждая: position absolute, border-radius 50%
// background: radial-gradient(circle, var(--spark) 0%, transparent 70%)
// animation: float-up ${duration}s ease-in infinite
// animation-delay: ${delay}s

// @keyframes float-up:
//   0%:   transform: translate(0, 0); opacity: 0
//   10%:  opacity: var(--ember-opacity)
//   90%:  opacity: var(--ember-opacity) * 0.3
//   100%: transform: translate(${sway}px, -100vh); opacity: 0

// Performance: will-change: transform, opacity
// Количество на мобильном: 20 (vs 40 на десктопе)
```

Дополнительно: 2-3 больших размытых blob-а (как в AmbientGlow), но оранжево-красных:

```typescript
// Blob 1: rgba(255,107,53,0.03), 500px, drift animation
// Blob 2: rgba(229,80,26,0.02), 400px, drift animation
// Blob 3: rgba(255,143,94,0.02), 350px, drift animation
```

### 9.10 Heat Overlay (замена GrainOverlay)

```typescript
// HeatOverlay.tsx — тонкий noise + heat haze effect
// Идентичен GrainOverlay по структуре, но с увеличенной opacity
// opacity: 0.04 (чуть больше чем 0.03 у VELVET)
// mixBlendMode: 'overlay'
// Дополнительно: CSS heat-distortion через SVG filter (опционально, может лагать)
```

---

## 10. СПЕЦИАЛЬНЫЕ КОМПОНЕНТЫ -- ДЕТАЛИ

### 10.1 XPProgressBar

```
Визуал:
  Track: 6px height, rounded-full, var(--ingot)
  Fill:  6px height, rounded-full
         background: linear-gradient(90deg, var(--molten) 0%, var(--spark) 60%, var(--ember) 100%)
         box-shadow: 0 0 8px rgba(255,107,53,0.4), 0 0 2px rgba(255,107,53,0.8)
         transition: width 0.8s cubic-bezier(0.16, 1, 0.3, 1)

  Текст над/под баром:
    Слева: "2,450 XP" (body-sm, var(--ash-white), font-numeric)
    Справа: "/ 5,000" (body-sm, var(--iron-dust))

  Или compact mode (без текста, только бар):
    height: 3px (тоньше)
    без текста

Props:
  current: number
  max: number
  showLabels?: boolean (default true)
  compact?: boolean (default false)
  animated?: boolean (default true)
```

### 10.2 StreakCounter

```
Визуал:
  Контейнер: inline-flex, items-center, gap-2
  Иконка: Flame (lucide), 20px
    Цвет:
      0 дней: var(--raw-iron) (потушен)
      1-6 дней: var(--spark)
      7-13 дней: var(--spark), animate-breathe (пульсация)
      14-29 дней: var(--ember), animate-breathe, glow-spark-sm
      30+ дней: var(--white-hot), animate-breathe, glow-spark-md
  Число: display стиль (24px, 800 weight, font-numeric)
    Цвет: var(--spark)
  Подпись: caption ("дней подряд"), var(--slag)

  При 0:
    Всё серое, иконка XCircle вместо Flame
    Текст: "Начни серию!"
```

### 10.3 TierBadge

5 тиров с уникальным визуалом:

```
BRONZE (Tier 1):
  bg: linear-gradient(135deg, rgba(205,127,50,0.15), rgba(205,127,50,0.05))
  border: 1px solid rgba(205,127,50,0.3)
  text: var(--tier-bronze) #CD7F32
  label: "БРОНЗА"
  icon: Shield (lucide)
  glow: none

IRON (Tier 2):
  bg: linear-gradient(135deg, rgba(113,121,126,0.15), rgba(113,121,126,0.05))
  border: 1px solid rgba(113,121,126,0.3)
  text: var(--tier-iron) #71797E
  label: "ЖЕЛЕЗО"
  icon: Shield (lucide)
  glow: none

STEEL (Tier 3):
  bg: linear-gradient(135deg, rgba(113,166,210,0.15), rgba(113,166,210,0.05))
  border: 1px solid rgba(113,166,210,0.3)
  text: var(--tier-steel) #71A6D2
  label: "СТАЛЬ"
  icon: ShieldCheck (lucide)
  glow: 0 0 10px rgba(113,166,210,0.15)

DAMASCUS (Tier 4):
  bg: linear-gradient(135deg, rgba(192,160,128,0.15), rgba(192,160,128,0.05))
  border: 1px solid rgba(192,160,128,0.3)
  text: var(--tier-damascus) #C0A080
  label: "ДАМАСК"
  icon: ShieldCheck (lucide)
  glow: 0 0 15px rgba(192,160,128,0.2)
  Дополнительно: волнистый паттерн (фон -- SVG pattern дамасской стали)

MYTHRIL (Tier 5):
  bg: linear-gradient(135deg, rgba(232,213,255,0.15), rgba(232,213,255,0.05))
  border: 1px solid rgba(232,213,255,0.4)
  text: var(--tier-mythril) #E8D5FF
  label: "МИФРИЛ"
  icon: Crown (lucide)
  glow: 0 0 15px rgba(232,213,255,0.3), 0 0 40px rgba(232,213,255,0.1)
  animation: animate-breathe (пульсирует)
  Дополнительно: shimmer gradient текста (text-gradient-heat но с purple/white)

Размеры badge:
  compact: h-6, px-2, text 10px (для списков)
  default: h-7, px-3, text 11px (для карточек)
  large: h-8, px-4, text 12px (для профиля)
```

### 10.4 AchievementCard

```
Визуал (unlocked):
  Контейнер: 72px width, flex flex-col items-center
  Иконка-бокс: 48px x 48px, rounded-xl
    bg: radial-gradient(circle, rgba(tier-color, 0.15) 0%, var(--soot) 70%)
    border: 1px solid rgba(tier-color, 0.25)
    Иконка: achievement-specific, 24px, цвет tier
  Название: 11px, var(--ash-white), text-center, line-clamp-2
  Margin-top: 6px

Визуал (locked):
  Иконка-бокс: 48px x 48px, rounded-xl
    bg: var(--ingot)
    border: 1px solid var(--cinder)
    Иконка: Lock, 18px, var(--raw-iron)
  Название: 11px, var(--iron-dust), text-center
  opacity: 0.45
  filter: grayscale(100%)

При тапе на unlocked:
  Haptic: light
  BottomSheet с деталями: название, описание, дата получения, tier
```

### 10.5 LessonCard

```
Визуал:
  Контейнер: card стиль, p-4, rounded-xl
  Ряд 1: [Иконка типа 20px] [Название урока] [Статус-иконка]
  Ряд 2: [Tier overline] [Длительность: "12 мин"]
  Ряд 3 (опционально): XPProgressBar compact

Состояния:
  COMPLETED:
    Border-left: 3px solid var(--tempered)
    Статус-иконка: CheckCircle2, var(--tempered)
    Opacity: 0.8 на всей карточке
  CURRENT:
    Border-left: 3px solid var(--spark)
    Статус-иконка: PlayCircle, var(--spark), animate-breathe
    Background: card-heated (subtle orange gradient)
  LOCKED:
    Border-left: 3px solid var(--cinder)
    Статус-иконка: Lock, var(--raw-iron)
    Opacity: 0.5
    Название: var(--iron-dust)

При тапе на CURRENT: navigate to Lesson
При тапе на COMPLETED: navigate to Lesson (review mode)
При тапе на LOCKED: haptic error, shake animation (x: [-4, 4, -4, 4, 0])
```

### 10.6 ExperimentCard (подробности в секции LAB выше)

---

## 11. RESPONSIVE BEHAVIOR

### Telegram Mini App Viewport

```
Минимальная ширина: 320px
Максимальная ширина: 480px (ограничиваем max-w-lg для контента)
Высота: динамическая (webApp.expand() раскрывает на весь экран)

Safe areas:
  Top: env(safe-area-inset-top) -- iOS notch
  Bottom: env(safe-area-inset-bottom) -- iOS home indicator
```

### Layout Strategy

```css
/* Основной контейнер */
.app {
  min-height: 100vh;
  min-height: 100dvh; /* dynamic viewport height для мобильных */
  padding-bottom: calc(64px + env(safe-area-inset-bottom)); /* навбар */
}

/* Навбар */
.navbar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: calc(64px + env(safe-area-inset-bottom));
  padding-bottom: env(safe-area-inset-bottom);
  z-index: 50;
}
```

### Keyboard Handling

```typescript
// Telegram WebApp автоматически управляет viewport при keyboard
// НО: на Android иногда fixed элементы прыгают

// Решение: при фокусе на input скрываем навбар
const [isKeyboardOpen, setIsKeyboardOpen] = useState(false)

useEffect(() => {
  const handleResize = () => {
    // Если viewport сильно уменьшился -- клавиатура открыта
    const isOpen = window.innerHeight < window.outerHeight * 0.75
    setIsKeyboardOpen(isOpen)
  }
  window.addEventListener('resize', handleResize)
  return () => window.removeEventListener('resize', handleResize)
}, [])

// В Navigation: {!isKeyboardOpen && <Navigation />}
```

### Pull-to-Refresh

Не реализуем кастомный pull-to-refresh. Причины:
1. Telegram WebApp не поддерживает его нативно
2. Конфликтует со скроллом
3. Данные обновляются при каждом открытии приложения + при переключении табов

Вместо этого: кнопка "Обновить" в нужных местах (Lab -> список экспериментов).

---

## 12. TAILWIND CONFIG

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // CRUCIBLE -- Backgrounds
        'forge-black': '#0A0A0A',
        'anvil': '#141414',
        'soot': '#1E1E1E',
        'ingot': '#262626',
        'cinder': '#333333',

        // CRUCIBLE -- Accents
        'spark': {
          DEFAULT: '#FF6B35',
          soft: '#FF8F5E',  // ember
          deep: '#E5501A',  // molten
        },
        'white-hot': '#FFF0E5',

        // CRUCIBLE -- Steel
        'steel': {
          DEFAULT: '#CBD5E1',
          brushed: '#94A3B8',
          oxidized: '#64748B',
          raw: '#475569',
        },

        // CRUCIBLE -- Text
        'ash-white': '#F0ECE5',
        'slag': '#9CA3AF',
        'iron-dust': '#6B7280',

        // Status
        'tempered': '#22C55E',
        'quench-fail': '#EF4444',
        'caution': '#F59E0B',
        'cooling': '#3B82F6',

        // Tiers
        'tier': {
          bronze: '#CD7F32',
          iron: '#71797E',
          steel: '#71A6D2',
          damascus: '#C0A080',
          mythril: '#E8D5FF',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      borderRadius: {
        'xl': '16px',
        '2xl': '20px',
      },
      boxShadow: {
        'forge-sm': '0 0 10px rgba(255, 107, 53, 0.2)',
        'forge-md': '0 0 20px rgba(255, 107, 53, 0.3)',
        'forge-lg': '0 0 40px rgba(255, 107, 53, 0.4)',
        'card': '0 4px 24px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.03)',
        'elevated': '0 12px 40px rgba(0, 0, 0, 0.7)',
      },
      animation: {
        'float-up': 'float-up var(--ember-duration, 15s) ease-in infinite',
        'breathe': 'breathe 3s ease-in-out infinite',
        'glow-pulse': 'glow-pulse 3s ease-in-out infinite',
        'heat-shimmer': 'heat-shimmer 4s ease-in-out infinite',
        'drift-1': 'drift-1 20s ease-in-out infinite',
        'drift-2': 'drift-2 25s ease-in-out infinite',
        'drift-3': 'drift-3 18s ease-in-out infinite',
        'shake': 'shake 0.4s ease-in-out',
      },
      keyframes: {
        'float-up': {
          '0%': { transform: 'translateY(0) translateX(0)', opacity: '0' },
          '10%': { opacity: 'var(--ember-opacity, 0.3)' },
          '90%': { opacity: 'calc(var(--ember-opacity, 0.3) * 0.3)' },
          '100%': { transform: 'translateY(-100vh) translateX(var(--ember-sway, 20px))', opacity: '0' },
        },
        'breathe': {
          '0%, 100%': { opacity: '0.7', transform: 'scale(1)' },
          '50%': { opacity: '1', transform: 'scale(1.03)' },
        },
        'glow-pulse': {
          '0%, 100%': { boxShadow: '0 0 15px rgba(255, 107, 53, 0.15)' },
          '50%': { boxShadow: '0 0 30px rgba(255, 107, 53, 0.3)' },
        },
        'heat-shimmer': {
          '0%, 100%': { backgroundPosition: '100% 0' },
          '50%': { backgroundPosition: '-100% 0' },
        },
        'drift-1': {
          '0%, 100%': { transform: 'translate(0, 0)' },
          '25%': { transform: 'translate(30px, -20px)' },
          '50%': { transform: 'translate(-10px, 30px)' },
          '75%': { transform: 'translate(20px, 10px)' },
        },
        'drift-2': {
          '0%, 100%': { transform: 'translate(0, 0)' },
          '25%': { transform: 'translate(-20px, 30px)' },
          '50%': { transform: 'translate(30px, -10px)' },
          '75%': { transform: 'translate(-10px, -30px)' },
        },
        'drift-3': {
          '0%, 100%': { transform: 'translate(0, 0)' },
          '33%': { transform: 'translate(20px, 20px)' },
          '66%': { transform: 'translate(-30px, 10px)' },
        },
        'shake': {
          '0%, 100%': { transform: 'translateX(0)' },
          '25%': { transform: 'translateX(-4px)' },
          '50%': { transform: 'translateX(4px)' },
          '75%': { transform: 'translateX(-4px)' },
        },
      },
    },
  },
  plugins: [],
}
```

---

## 13. СПИСОК ДОСТИЖЕНИЙ (для AchievementCard)

| ID | Название | Описание | Условие | Tier |
|----|----------|----------|---------|------|
| `first_spark` | Первая искра | Пройди первый урок | 1 урок | bronze |
| `streak_7` | Неделя у горна | 7 дней подряд | streak 7 | bronze |
| `streak_14` | Двойная закалка | 14 дней подряд | streak 14 | iron |
| `streak_30` | Месяц в кузне | 30 дней подряд | streak 30 | steel |
| `streak_100` | Мастер огня | 100 дней подряд | streak 100 | mythril |
| `lessons_5` | Подмастерье | 5 уроков пройдено | 5 lessons | bronze |
| `lessons_15` | Ремесленник | 15 уроков | 15 lessons | iron |
| `lessons_30` | Кузнец | 30 уроков | 30 lessons | steel |
| `exp_first` | Первый эксперимент | Создай первый эксперимент | 1 experiment | bronze |
| `exp_5` | Лаборант | 5 экспериментов | 5 experiments | iron |
| `exp_complete` | Довёл до конца | Заверши эксперимент | 1 completed | iron |
| `exp_10` | Испытатель | 10 экспериментов | 10 experiments | steel |
| `tier_iron` | Железная воля | Достигни Tier 2 | tier = iron | iron |
| `tier_steel` | Стальной характер | Достигни Tier 3 | tier = steel | steel |
| `tier_damascus` | Дамасский клинок | Достигни Tier 4 | tier = damascus | damascus |
| `tier_mythril` | Мифрил | Достигни Tier 5 | tier = mythril | mythril |
| `all_paths` | Мастер на все руки | Начни все 3 пути | 3 paths started | steel |
| `speed_lesson` | Скоростная ковка | Пройди урок за 5 минут | lesson < 5min | bronze |
| `night_owl` | Ночная смена | Пройди урок после 00:00 | lesson after midnight | iron |
| `comeback` | Возвращение к горну | Вернись после 7+ дней перерыва | gap >= 7 days | iron |

Всего: 20 достижений. Иконки: lucide-react (`Sparkles`, `Flame`, `Shield`, `Hammer`, `Crown`, `Zap`, `Trophy`, `Clock`, `Moon`, `RotateCcw` и т.д.)

---

## 14. CSS COMPONENT CLASSES

```css
/* ===== CRUCIBLE Component Classes ===== */

@layer components {
  /* Card base */
  .card {
    @apply p-4 rounded-xl;
    background: var(--soot);
    border: 1px solid var(--cinder);
    box-shadow: var(--shadow-card);
    will-change: transform;
  }

  .card:hover {
    border-color: rgba(255, 107, 53, 0.12);
  }

  .card-heated {
    background: linear-gradient(
      135deg,
      rgba(255, 107, 53, 0.04) 0%,
      var(--soot) 40%,
      var(--soot) 100%
    );
  }

  /* Buttons */
  .btn {
    @apply px-5 py-2.5 font-semibold rounded-lg;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .btn-primary {
    background: linear-gradient(135deg, var(--spark) 0%, var(--molten) 100%);
    color: white;
    box-shadow: 0 4px 16px rgba(255, 107, 53, 0.3);
  }

  .btn-primary:hover {
    box-shadow: 0 8px 24px rgba(255, 107, 53, 0.4);
  }

  .btn-primary:active {
    transform: scale(0.97);
  }

  .btn-secondary {
    background: rgba(255, 107, 53, 0.1);
    color: var(--ash-white);
    border: 1px solid rgba(255, 107, 53, 0.2);
  }

  .btn-secondary:hover {
    background: rgba(255, 107, 53, 0.15);
    border-color: rgba(255, 107, 53, 0.3);
  }

  .btn-ghost {
    background: transparent;
    color: var(--slag);
  }

  .btn-ghost:hover {
    background: rgba(255, 255, 255, 0.05);
    color: var(--ash-white);
  }

  /* Input */
  .input {
    @apply w-full px-4 py-3 text-sm rounded-lg;
    background: rgba(10, 10, 10, 0.8);
    color: var(--ash-white);
    border: 1px solid var(--cinder);
    transition: all 0.3s ease;
  }

  .input:focus {
    outline: none;
    border-color: var(--spark);
    box-shadow: 0 0 0 3px rgba(255, 107, 53, 0.1);
  }

  .input::placeholder {
    color: var(--iron-dust);
  }

  /* Glass */
  .glass {
    background: rgba(20, 20, 20, 0.85);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 107, 53, 0.06);
  }

  /* Overline */
  .overline {
    @apply text-xs font-semibold tracking-widest uppercase;
    font-size: 11px;
    letter-spacing: 0.12em;
    color: var(--iron-dust);
  }

  /* Gradient text */
  .text-gradient-heat {
    background: linear-gradient(90deg, var(--ember), var(--spark), var(--white-hot), var(--spark), var(--ember));
    background-size: 200% 100%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: heat-shimmer 4s ease-in-out infinite;
  }

  /* Shimmer skeleton */
  .shimmer {
    background: linear-gradient(
      90deg,
      var(--soot) 0%,
      var(--ingot) 50%,
      var(--soot) 100%
    );
    background-size: 200% 100%;
    animation: shimmer 1.5s linear infinite;
    border-radius: 8px;
  }

  /* Chip */
  .chip {
    @apply px-3 py-1.5 rounded-full text-xs font-medium;
    background: var(--ingot);
    color: var(--slag);
    border: 1px solid var(--cinder);
  }

  .chip.active {
    background: var(--spark);
    color: white;
    border-color: transparent;
  }

  /* Divider */
  .divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--cinder), transparent);
  }
}
```

---

## 15. FILE STRUCTURE (предполагаемая)

```
forge_miniapp/
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── index.css                    # CRUCIBLE theme + component classes
│       ├── vite-env.d.ts
│       │
│       ├── hooks/
│       │   ├── useTelegram.ts           # Telegram WebApp hook (reuse)
│       │   ├── useAuth.ts
│       │   └── useKeyboard.ts           # Keyboard detection
│       │
│       ├── lib/
│       │   ├── animations.tsx           # Spring presets, variants, AnimatedNumber
│       │   └── constants.ts             # Tiers, achievements data
│       │
│       ├── api/
│       │   └── client.ts               # API client
│       │
│       ├── components/
│       │   ├── Navigation.tsx           # Bottom tab bar
│       │   ├── EmberField.tsx           # Background floating sparks
│       │   ├── HeatOverlay.tsx          # Grain/noise overlay
│       │   ├── Loading.tsx              # Loading state
│       │   ├── Skeleton.tsx             # Shimmer skeleton
│       │   ├── BottomSheet.tsx          # Bottom sheet modal
│       │   ├── Toast.tsx               # XP gain / notification toast
│       │   ├── XPProgressBar.tsx
│       │   ├── StreakCounter.tsx
│       │   ├── TierBadge.tsx
│       │   ├── StatBlock.tsx
│       │   ├── ActionButton.tsx
│       │   ├── LessonCard.tsx
│       │   ├── ExperimentCard.tsx
│       │   ├── AchievementCard.tsx
│       │   ├── PathNode.tsx
│       │   ├── CalendarGrid.tsx
│       │   └── TierUpCelebration.tsx    # Full-screen tier up animation
│       │
│       └── pages/
│           ├── Home.tsx
│           ├── Path.tsx
│           ├── Lesson.tsx
│           ├── Lab.tsx
│           └── Profile.tsx
│
└── backend/                             # (отдельная задача)
    ├── api/
    ├── models/
    └── services/
```

---

## 16. СРАВНЕНИЕ ТРЁХ ТЕМАТИК

| Аспект | VELVET | COSMOS | CRUCIBLE |
|--------|--------|--------|----------|
| Температура | Тёплый | Холодный | Горячий |
| Метафора | Бархат, роскошь | Космос, звёзды | Кузница, огонь |
| Фон | Чёрно-коричневый | Чёрно-синий | Чёрный (нейтральный) |
| Акцент | Amber/Gold | Indigo/Purple | Orange/Red |
| Фон-эффект | AmbientGlow (blobs) | Stars (parallax) | EmberField (particles up) |
| Overlay | GrainOverlay (3%) | -- | HeatOverlay (4%) |
| Card border | smoke | indigo glow | cinder -> spark glow |
| Кнопка primary | Gold gradient | Indigo gradient | Orange gradient |
| Настроение | Спокойное, luxury | Мечтательное, далёкое | Энергичное, действие |
| Border radius | 16-24px (мягкий) | 16-24px (мягкий) | 12-16px (чуть жёстче) |

---

## 17. PERFORMANCE NOTES

1. **EmberField**: максимум 30 частиц на мобильном, 40 на десктопе. Использовать `will-change: transform, opacity`. Частицы -- чистые div с CSS animation (не canvas, чтобы не конфликтовать с confetti).

2. **Confetti**: canvas-confetti автоматически создаёт и уничтожает canvas. Использовать только для событий (achievement, tier up, streak milestone).

3. **framer-motion**: использовать `layout` prop осторожно -- не на списках более 20 элементов. Для Path nodes вместо `layout` использовать обычные `initial/animate`.

4. **Иконки**: lucide-react поддерживает tree-shaking, импортировать только нужные: `import { Flame } from 'lucide-react'`.

5. **Fonts**: Inter -- системный шрифт на многих устройствах. Подключать через Google Fonts только `wght@400;500;600;700;800` (5 весов).

6. **Images**: Вся графика -- иконки (lucide) + CSS (градиенты, тени). Никаких растровых изображений. Это обеспечивает мгновенную загрузку.

---

*Документ создан: 18 февраля 2026*
*Версия: 1.0*
*Автор: Design System Spec для FORGE Mini App*
