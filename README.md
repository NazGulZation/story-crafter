# Stories Workspace

A dedicated workspace for creative writing, narrative fiction, worldbuilding, and serialized storytelling. Stories are organized into dedicated project directories named after each narrative work, retaining the standardized four-pillar folder architecture (`chapters/`, `characters/`, `outlines/`, `world/`).

---

## Workspace Directory Architecture

```text
Stories/
├── GEMINI.md                                  # Global project rules, forbidden tropes, & writing constraints
├── README.md                                  # Workspace overview & story catalog
├── .agents/
│   └── skills/
│       └── story-writing/                     # Workspace creative writing skill
│           └── SKILL.md
└── the_rogue_prince_of_blackweir/             # Active Story Project
    ├── chapters/                              # 10 completed chapters
    │   ├── ch01_the_silver_smirk.md
    │   ├── ch02_flea_bottom_on_the_chasm.md
    │   ├── ch03_the_king_of_the_stepstones.md
    │   ├── ch04_the_rot_in_the_gold.md
    │   ├── ch05_fire_and_crucible.md
    │   ├── ch06_the_broken_vanguard.md
    │   ├── ch07_the_scraps_of_althea.md
    │   ├── ch08_the_gods_eye_in_the_arena.md
    │   ├── ch09_the_banishment_of_the_vain.md
    │   └── ch10_the_sovereign_of_the_ash.md
    ├── characters/                            # Character dossiers & voice registers
    │   └── dossiers.md
    ├── outlines/                              # Arc breakdown & beat sheets
    │   └── arc_outline.md
    └── world/                                 # Setting bibles, geography & ecology
        └── setting_and_lore.md
```

---

## Story Catalog

### [The Rogue Prince of Blackweir](file:///c:/StoryCrafter/the_rogue_prince_of_blackweir/)
- **Status**: Complete (10 Chapters).
- **Core Premise**: Following the fatal plunge at the Gods Eye, the soul of Prince Daemon Targaryen awakens in the discarded, broken-hearted shell of Caspar Thorne—the betrayed logistical mastermind of an arrogant hero's party.
- **Key Milestones**:
  - [Chapter 1](file:///c:/StoryCrafter/the_rogue_prince_of_blackweir/chapters/ch01_the_silver_smirk.md): The tavern betrayal and Daemon Targaryen's awakening.
  - [Chapter 8](file:///c:/StoryCrafter/the_rogue_prince_of_blackweir/chapters/ch08_the_gods_eye_in_the_arena.md): **The Climax & Catharsis** — The brutal public arena duel where Daemon shatters Lysander's vanity and holy blessings.
  - [Chapter 10](file:///c:/StoryCrafter/the_rogue_prince_of_blackweir/chapters/ch10_the_sovereign_of_the_ash.md): The ascent of the Citadel of the Red Kilns and sovereign preparation for war.

### [The Mockingbird's Ledger](file:///c:/StoryCrafter/the_mockingbirds_ledger/)
- **Status**: Complete (15 Chapters, 2 Arcs).
- **Core Premise**: Following his execution at Winterfell, the soul of Lord Petyr Baelish awakens in the starved, broken-hearted body of Alden Croft—banished five years prior by a gilded "Hero" and three treacherous women who shared his bed.
- **Structure**:
  - **Arc 1 (Chapters 1–9)**: *The Foundations of Debt* — The gutter awakening, economic reconnaissance, the whisper network of *The Brazen Quill*, and cornering the realm's grain, arms, and sovereign bonds.
  - **Arc 2 (Chapters 10–15)**: *The Sovereign Audit & Catharsis (Climax Arc)* — Commencing at Chapter 10, the systemic default of the realm, military mutiny, religious downfall, the psychological destruction of the childhood friend, and the public ruin of Lord Godfrey Sterling.
- **Key Milestones**:
  - [Chapter 1](file:///c:/StoryCrafter/the_mockingbirds_ledger/chapters/ch01_the_gutter_and_the_mockingbird.md): Awakening in the gutter and the memory of betrayal.
  - [Chapter 10](file:///c:/StoryCrafter/the_mockingbirds_ledger/chapters/ch10_the_sovereign_audit.md): **The Climax Arc Begins** — The midnight Sovereign Audit and declaration of kingdom bankruptcy.
  - [Chapter 14](file:///c:/StoryCrafter/the_mockingbirds_ledger/chapters/ch14_the_hero_unmade.md): The poisoning, arrest, and public shaming of Godfrey Sterling.
  - [Chapter 15](file:///c:/StoryCrafter/the_mockingbirds_ledger/chapters/ch15_the_mockingbirds_realm.md): Lord Protector Petyr Baelish sovereign atop the High Citadel.

---

## Desktop Book Reader (One-Click Launch)

A sleek, book-style desktop application for reading all stories in this workspace:
- **Launch via Executable**: Double-click [`StoryReader.exe`](file:///c:/StoryCrafter/StoryReader.exe). It checks/installs Python, initializes the local `.venv`, installs requirements, and opens the reader with an embedded custom vector book icon.
- **Launch via Batch**: Double-click [`run_reader.bat`](file:///c:/StoryCrafter/run_reader.bat).
- **Direct Python Launch**: `.\.venv\Scripts\python.exe reader_app.py`.
- **Features**:
  - Two-page book spread with spine crease effect or continuous reading mode.
  - Dynamic responsive DOM pagination that reflows across pages on maximize/resize while preserving font size.
  - Clean chapter transitions (starts on Page 1 & 2 when moving forward, ends on final spread when reversing).
  - Directional paper swish animations (right-to-left for next, left-to-right for prev).
  - Web Audio API synthesized crisp paper swipe sound effect with top bar toggle and keyboard shortcut (`S`).
  - Classical book typography with gilded drop caps, fleurons, and running headers.
  - Parchment, Warm Sepia, Midnight, and Clean Paper themes.
  - Story selector, Table of Contents drawer, font sizing, and reading progress auto-save.

---

## Active Constraints & Writing Rules

All story drafts, character sheets, and lore documents within this workspace adhere strictly to the rules in [GEMINI.md](file:///d:/Documents/Stories/GEMINI.md):

1. **Strictly Forbidden Names & Tropes**:
   - `Sunken Pass`, `Oakhaven`, `Julian`, `Rian`, `Mia`, `Elyria`, `Whispering Wood`, `Dragon/Drakes`, `Garrick`, `Bram`, `Vaelrian`, `Vane`, `Aethelgard`, `Harrick`, `Varis`, `Corin`, `Silas`, `Monster Crawler`, `Monster Dog`, `Sunken Crypt/Hollow`.
   - `Opening Alley Thug / Mugger Encounter`: No brawling with or looting street muggers in opening chapters.
   - `Accountant Assistant / Junior Ledger Clerk Subordination`: No subordinate bookkeeper or clerk employment; protagonist must rise through independent commercial leverage and arbitrage.
2. **Anti-Deus Ex Machina & Mandatory Foreshadowing**:
   - No ass-pulls or unearned plot conveniences.
   - All climactic resolutions, critical skills, or turning points must be seeded and foreshadowed beforehand (Chekhov's Arsenal).
   - Events advance through logical causality (*"Therefore / But"* instead of *"And then / Suddenly"*).
3. **Prose Quality & Anti-AI Hallmarks**:
   - Ground scenes in at least three non-visual senses.
   - Strip AI clichés (e.g. "breath she didn't know she was holding", melodramatic shivers, overused metaphors).
   - Subtextual dialogue reflecting status, tension, and deflection.
