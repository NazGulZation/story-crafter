# Branching Graph: *Onii-chan Route*

A choice-driven explicit interactive story across **5 tiers of depth** culminating in **6 unique endings**, strictly rooted at Chapter 1 with zero convergence.

---

## Complete Mermaid Diagram

```mermaid
flowchart TD
    classDef root fill:#4a154b,stroke:#fff,stroke-width:2px,color:#fff;
    classDef tier2 fill:#1f4068,stroke:#fff,stroke-width:1.5px,color:#fff;
    classDef tier3 fill:#2d3748,stroke:#fff,stroke-width:1.5px,color:#fff;
    classDef tier4 fill:#1a365d,stroke:#fff,stroke-width:1.5px,color:#fff;
    classDef ending fill:#162447,stroke:#e43f5a,stroke-width:2px,color:#fff;

    subgraph "Tier 1: Root Dilemma"
        T1["ch01_coming_home.md<br/>🎮 Midnight Entry & Blaring Speakers"]:::root
    end

    subgraph "Tier 2: Primary Dynamic Forks"
        T2A["ch02a_collapse_and_enable.md<br/>🛋️ Surrender / Enable Branch"]:::tier2
        T2B["ch02b_confront_the_boundary.md<br/>⚡ Confront / Resist Branch"]:::tier2
    end

    subgraph "Tier 3: Escalation Sub-Branches"
        T3A1["ch03a1_the_nightly_migration.md<br/>🌙 Nightly Bed Infiltration<br/>⟨choice⟩"]:::tier3
        T3A2["ch03a2_the_eroge_recreation.md<br/>🎮 Eroge Scene Adaptation<br/>⟨progression⟩"]:::tier3
        T3B1["ch03b1_the_naked_apron.md<br/>🍳 Naked Apron 'Service'<br/>⟨progression⟩"]:::tier3
        T3B2["ch03b2_the_jealousy_trigger.md<br/>📱 Coworker LINE Discovery<br/>⟨choice⟩"]:::tier3
    end

    subgraph "Tier 4: Climax Setup & Hardcore Encounters"
        T4A1A["ch04a1a_the_domestic_sinkhole.md<br/>🍜 Full Domestic Lethargy"]:::tier4
        T4A1B["ch04a1b_feigned_slumber.md<br/>💤 Midnight Wandering Hands"]:::tier4
        T4A2["ch04a2_the_wardrobe_raid.md<br/>🎭 Full Cosplay Preparation"]:::tier4
        T4B1["ch04b1_unconditional_service.md<br/>👑 Unrestrained Maid Demands"]:::tier4
        T4B2A["ch04b2a_the_collar_marks.md<br/>💋 Visible Territorial Bites"]:::tier4
        T4B2B["ch04b2b_the_live_mic.md<br/>🎙️ Unmuted Hot Microphone"]:::tier4
    end

    subgraph "Tier 5: Dedicated Terminal Endings (All 6 in Tier 5)"
        E1["ending01_were_so_cooked.md<br/>🔥 Ending 1: We're So Cooked"]:::ending
        E2["ending02_sleep_escalation.md<br/>🌙 Ending 2: Sleep Escalation"]:::ending
        E3["ending03_cosplay_conditioning.md<br/>🎭 Ending 3: Cosplay Conditioning"]:::ending
        E4["ending04_role_reversal_service.md<br/>👑 Ending 4: Role Reversal Service"]:::ending
        E5["ending05_marking_claiming.md<br/>🔒 Ending 5: Marking / Claiming"]:::ending
        E6["ending06_livestream_accident.md<br/>📸 Ending 6: Livestream Accident"]:::ending
    end

    %% Tier 1 to Tier 2
    T1 -->|"Crash on the bed next to her"| T2A
    T1 -->|"Stand in the door and lay down the law"| T2B

    %% Tier 2 to Tier 3
    T2A -->|"Let her stay in your bed"| T3A1
    T2A -->|"Grab the spare controller and play along"| T3A2

    T2B -->|"Call her bluff on 'earning her keep'"| T3B1
    T2B -->|"Ignore her teasing and check your work phone"| T3B2

    %% Tier 3 to Tier 4
    T3A1 -->|"Surrender completely to the sluggish warmth"| T4A1A
    T3A1 -->|"Pretend to sleep while she crawls over you"| T4A1B

    T3A2 -->|"Let her raid the cosplay box for the 'true route'"| T4A2

    T3B1 -->|"Hold her to her maid contract without mercy"| T4B1

    T3B2 -->|"Tilt your neck and let her leave her bite marks"| T4B2A
    T3B2 -->|"Try to shove her away toward her streaming desk"| T4B2B

    %% Tier 4 to Tier 5
    T4A1A --> E1
    T4A1B --> E2
    T4A2 --> E3
    T4B1 --> E4
    T4B2A --> E5
    T4B2B --> E6
```

---

## Path Directory & Verification

| Path | Tier 1 | Tier 2 | Tier 3 | Tier 4 | Tier 5 (Ending) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Path 1** | `ch01_coming_home.md` | `ch02a_collapse_and_enable.md` | `ch03a1_the_nightly_migration.md` | `ch04a1a_the_domestic_sinkhole.md` | `ending01_were_so_cooked.md` |
| **Path 2** | `ch01_coming_home.md` | `ch02a_collapse_and_enable.md` | `ch03a1_the_nightly_migration.md` | `ch04a1b_feigned_slumber.md` | `ending02_sleep_escalation.md` |
| **Path 3** | `ch01_coming_home.md` | `ch02a_collapse_and_enable.md` | `ch03a2_the_eroge_recreation.md` | `ch04a2_the_wardrobe_raid.md` | `ending03_cosplay_conditioning.md` |
| **Path 4** | `ch01_coming_home.md` | `ch02b_confront_the_boundary.md` | `ch03b1_the_naked_apron.md` | `ch04b1_unconditional_service.md` | `ending04_role_reversal_service.md` |
| **Path 5** | `ch01_coming_home.md` | `ch02b_confront_the_boundary.md` | `ch03b2_the_jealousy_trigger.md` | `ch04b2a_the_collar_marks.md` | `ending05_marking_claiming.md` |
| **Path 6** | `ch01_coming_home.md` | `ch02b_confront_the_boundary.md` | `ch03b2_the_jealousy_trigger.md` | `ch04b2b_the_live_mic.md` | `ending06_livestream_accident.md` |
