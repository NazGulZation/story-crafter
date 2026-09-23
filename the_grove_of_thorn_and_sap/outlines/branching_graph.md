# Branching Graph: *The Grove of Thorn and Sap*

A choice-driven NSFW interactive story across **5 levels of depth** culminating in **6 unique endings**.

---

## Complete Mermaid Diagram

```mermaid
flowchart TD
    T1["Tier 1 (SFW): ch01_the_deep_patrol.md<br/>⚔️ The Capture"]

    T2A["Tier 2 (NSFW): ch02a_submit_to_the_circle.md<br/>🌿 Gentle Claiming"]
    T2B["Tier 2 (NSFW): ch02b_resist_the_binding.md<br/>🩸 Rough Claiming"]

    T3A1["Tier 3: ch03a1_the_circle_ritual.md<br/>🌸 Full Circle Claims You<br/>⟨choice⟩"]
    T3A2["Tier 3: ch03a2_the_elder_claims_you.md<br/>🌳 Elder Intimate Scene<br/>⟨linear⟩"]
    T3B1["Tier 3: ch03b1_break_the_vine.md<br/>💥 Escape Attempt<br/>⟨linear⟩"]
    T3B2["Tier 3: ch03b2_endure_in_silence.md<br/>🤫 Stillness Earns Respect<br/>⟨choice⟩"]

    T4A["Tier 4: ch04a1a_drink_the_sap.md<br/>🍯 Transformation Ritual"]
    T4B["Tier 4: ch04a1b_refuse_the_draught.md<br/>❌ Expulsion & Contamination"]
    T4C["Tier 4: ch04a2_the_elder_bond.md<br/>👑 The Elder's Offer"]
    T4D["Tier 4: ch04b1_the_scarred_flight.md<br/>🏃 Forest Gauntlet"]
    T4E["Tier 4: ch04b2a_the_thorn_pact.md<br/>🤝 Negotiated Freedom"]
    T4F["Tier 4: ch04b2b_the_grove_heart.md<br/>🌱 The Heartwood Chamber"]

    E1["🌿 ending01_the_rooted_consort.md<br/>Ending 1: The Rooted Consort"]
    E2["💔 ending02_the_cracked_vessel.md<br/>Ending 2: The Cracked Vessel"]
    E3["👑 ending03_the_elder_bloom.md<br/>Ending 3: The Elder's Bloom"]
    E4["🩸 ending04_the_scarred_deserter.md<br/>Ending 4: The Scarred Deserter"]
    E5["🤝 ending05_the_thorn_pact.md<br/>Ending 5: The Thorn Pact"]
    E6["🌱 ending06_the_seed_bearer.md<br/>Ending 6: The Seed-Bearer"]

    T1 -->|"Submit to the Circle"| T2A
    T1 -->|"Resist the Binding"| T2B

    T2A -->|"Accept the Circle's Full Ritual"| T3A1
    T2A -->|"Offer Yourself to the Elder Alone"| T3A2

    T2B -->|"Fight Harder"| T3B1
    T2B -->|"Go Still and Endure"| T3B2

    T3A1 -->|"Drink the Sap-Draught"| T4A
    T3A1 -->|"Refuse the Draught"| T4B

    T3A2 -.->|"linear"| T4C

    T3B1 -.->|"linear"| T4D

    T3B2 -->|"Speak a Bargain"| T4E
    T3B2 -->|"Offer Yourself to the Grove-Heart"| T4F

    T4A --> E1
    T4B --> E2
    T4C --> E3
    T4D --> E4
    T4E --> E5
    T4F --> E6
```

---

## Path Directory & Verification

| Path | Tier 1 | Tier 2 | Tier 3 | Tier 4 | Tier 5 (Ending) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Path 1** | `ch01_the_deep_patrol.md` | `ch02a_submit_to_the_circle.md` | `ch03a1_the_circle_ritual.md` | `ch04a1a_drink_the_sap.md` | `ending01_the_rooted_consort.md` |
| **Path 2** | `ch01_the_deep_patrol.md` | `ch02a_submit_to_the_circle.md` | `ch03a1_the_circle_ritual.md` | `ch04a1b_refuse_the_draught.md` | `ending02_the_cracked_vessel.md` |
| **Path 3** | `ch01_the_deep_patrol.md` | `ch02a_submit_to_the_circle.md` | `ch03a2_the_elder_claims_you.md` | `ch04a2_the_elder_bond.md` | `ending03_the_elder_bloom.md` |
| **Path 4** | `ch01_the_deep_patrol.md` | `ch02b_resist_the_binding.md` | `ch03b1_break_the_vine.md` | `ch04b1_the_scarred_flight.md` | `ending04_the_scarred_deserter.md` |
| **Path 5** | `ch01_the_deep_patrol.md` | `ch02b_resist_the_binding.md` | `ch03b2_endure_in_silence.md` | `ch04b2a_the_thorn_pact.md` | `ending05_the_thorn_pact.md` |
| **Path 6** | `ch01_the_deep_patrol.md` | `ch02b_resist_the_binding.md` | `ch03b2_endure_in_silence.md` | `ch04b2b_the_grove_heart.md` | `ending06_the_seed_bearer.md` |
