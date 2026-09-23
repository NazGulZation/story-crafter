# The Vermillion Route (朱の道)

An explicit interactive romance and erotica novel set in contemporary Kyoto, featuring an original licensed tour guide, **Chinatsu Ibuki (伊吹 千夏)**.

---

## Story Overview
- **Title**: The Vermillion Route (朱の道)
- **Genre**: Interactive Fiction, NSFW / Contemporary Erotica, Romance
- **Format**: 4 Levels, Balanced Binary Tree, 8 Distinct Terminal Endings
- **Total Word Count**: ~27,123 words across 15 chapters
- **POV**: First-person (unnamed reader-insert)
- **Tense**: Past tense
- **Setting**: Kyoto, Japan (Fushimi Inari Taisha, Arashiyama Bamboo Grove, Pontochō, Ryokan Suimei-an, Higashiyama, Kennin-ji)

---

## Interactive Branching Architecture

```mermaid
flowchart TD
    CH01["Level 1: The Vermillion Gate<br/>(Fushimi Inari Taisha)"]

    CH01 -->|"Follow the marked trail<br/>(Safe, patient)"| CH02A["Level 2A: Bamboo Patience<br/>(Arashiyama River Bench)"]
    CH01 -->|"Take her hidden shortcut<br/>(Bold, private)"| CH02B["Level 2B: The Fox Detour<br/>(Hidden Fox Shrine)"]

    CH02A -->|"Accept her dinner invitation<br/>(Pontochō riverside)"| CH03A["Level 3A: Pontochō Lanterns<br/>(Under-table touching)"]
    CH02A -->|"Suggest the ryokan cedar bath<br/>(Direct, sensual)"| CH03B["Level 3B: Cedar Steam<br/>(Cedar bath & wet futon)"]

    CH02B -->|"Escalate against the shrine wall<br/>(Immediate outdoor sex)"| CH03C["Level 3C: Stone Garden Heat<br/>(Oral & standing rear)"]
    CH02B -->|"Step back, build the tension<br/>(Delayed gratification walk)"| CH03D["Level 3D: The Slow Burn<br/>(Higashiyama dirty talk)"]

    CH03A -->|"Follow her to her apartment<br/>(Intimate, domestic)"| E1["Ending 1: Her Tatami<br/>(Slow missionary on tatami)"]
    CH03A -->|"Pull her into the dark alley<br/>(Frantic, risky)"| E2["Ending 2: The Alley Lantern<br/>(Standing against cedar wall)"]

    CH03B -->|"Let her ride you on the wet futon<br/>(Languorous, deep)"| E3["Ending 3: Hot Spring Surrender<br/>(Arched-back cowgirl)"]
    CH03B -->|"Take her from behind on the rush mats<br/>(Urgent, splashing)"| E4["Ending 4: The Futon Tangle<br/>(Doggy into deep missionary)"]

    CH03C -->|"Pin her to the moss and finish inside<br/>(Primal, earthy)"| E5["Ending 5: Moss and Stone<br/>(Ancient wall to moss collapse)"]
    CH03C -->|"Let her take the reins and pin your wrists<br/>(Femdom guide command)"| E6["Ending 6: The Guide's Command<br/>(Guide commands the route)"]

    CH03D -->|"Break under her touch in the taxi<br/>(Confined, rain-slicked)"| E7["Ending 7: Backseat Confession<br/>(Cramped taxi lap sex)"]
    CH03D -->|"Check in and close the heavy hotel door<br/>(Deluxe, exhaustive)"| E8["Ending 8: Room 407<br/>(Complete multi-round arc)"]
```

---

## Directory Structure
- `chapters/`: 15 chapter markdown files (7 branching nodes + 8 terminal endings).
- `characters/`: Complete profile for Chinatsu Ibuki (`chinatsu_ibuki.md`).
- `world/`: Authentic Kyoto locations and architectural/sensory anchors (`kyoto_locations.md`).
- `outlines/`: Arc design, branching logic, and clothing/state tracking ledger (`arc_outline.md`).
