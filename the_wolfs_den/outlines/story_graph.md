# Story Graph & Narrative Architecture: The Wolf's Den

## 1. High-Concept & Narrative Overview

- **Title**: The Wolf's Den (狼の巣)
- **Story ID**: `the_wolfs_den`
- **Setting**: Caon Guildhall — Post-Training Evening Cool-Down.
- **Protagonist**: Yuuki (Princess Knight) — First-Person POV ("I").
- **Cast**: Makoto (Wolf), Kaori (Dog), Kasumi (Doberman), Maho (Fox).
- **Catalyst**: Organic post-training exhaustion, shared proximity, and unshielded intimacy.
- **Graph Topology**: Pure directed out-tree (arborescence). In-degree = 1 for all non-root nodes. 100% path isolation. Zero convergence. Total 31 chapters, 9 terminal endings ($E \ge B$).

---

## 2. Interactive Story Graph (Full Mermaid Flowchart)

```mermaid
flowchart TD
    %% TIER 1: ROOT
    CH01["<b>ch01_sweat_and_steel.md</b><br/><i>Tier 1: Sweat & Steel (Root)</i>"]

    %% TIER 2: BRANCHES (SFW Buildup & Tension)
    CH02A["<b>ch02a_the_wolfs_kitchen.md</b><br/><i>Tier 2A: The Wolf's Kitchen</i>"]
    CH02B["<b>ch02b_steam_and_stone.md</b><br/><i>Tier 2B: Steam & Stone</i>"]
    CH02C["<b>ch02c_the_foxs_chamber.md</b><br/><i>Tier 2C: The Fox's Chamber</i>"]

    %% TIER 3: MID-ARCS (NSFW Foreplay Begins)
    CH03A1["<b>ch03a1_fangs_and_claws.md</b><br/><i>Tier 3A1: Fangs & Claws</i>"]
    CH03A2["<b>ch03a2_the_wolfs_musk.md</b><br/><i>Tier 3A2: The Wolf's Musk</i>"]
    CH03A3["<b>ch03a3_the_detectives_reprimand.md</b><br/><i>Tier 3A3: The Detective's Reprimand</i>"]
    CH03A4["<b>ch03a4_predator_and_vixen.md</b><br/><i>Tier 3A4: Predator & Vixen</i>"]
    CH03A5["<b>ch03a5_midnight_foragers.md</b><br/><i>Tier 3A5: Midnight Foragers</i>"]
    CH03B1["<b>ch03b1_nankurunaisa.md</b><br/><i>Tier 3B1: Nankurunaisa</i>"]
    CH03B2["<b>ch03b2_the_detectives_hypothesis.md</b><br/><i>Tier 3B2: The Detective's Hypothesis</i>"]
    CH03C1["<b>ch03c1_once_upon_a_night.md</b><br/><i>Tier 3C1: Once Upon a Night</i>"]
    CH03C2["<b>ch03c2_the_packs_arrival.md</b><br/><i>Tier 3C2: The Pack's Arrival</i>"]

    %% TIER 4: CLIMAXES (Full Explicit Penetration & Mind-Break)
    CH04A1["<b>ch04a1_alpha_claim.md</b><br/><i>Tier 4A1: Alpha Claim</i>"]
    CH04A2["<b>ch04a2_drenched.md</b><br/><i>Tier 4A2: Drenched</i>"]
    CH04A3["<b>ch04a3_interrogation_under_fire.md</b><br/><i>Tier 4A3: Interrogation Under Fire</i>"]
    CH04A4["<b>ch04a4_crown_and_claw.md</b><br/><i>Tier 4A4: Crown & Claw</i>"]
    CH04A5["<b>ch04a5_untamed_stamina.md</b><br/><i>Tier 4A5: Untamed Stamina</i>"]
    CH04B1["<b>ch04b1_broken_mantra.md</b><br/><i>Tier 4B1: Broken Mantra</i>"]
    CH04B2["<b>ch04b2_case_closed.md</b><br/><i>Tier 4B2: Case Closed</i>"]
    CH04C1["<b>ch04c1_the_princes_conquest.md</b><br/><i>Tier 4C1: The Prince's Conquest</i>"]
    CH04C2["<b>ch04c2_full_pack.md</b><br/><i>Tier 4C2: Full Pack</i>"]

    %% TIER 5: TERMINAL ENDINGS
    E1["<b>ending01_the_wolfs_mark.md</b><br/><i>Ending 1: The Wolf's Mark</i>"]
    E2["<b>ending02_salt_and_musk.md</b><br/><i>Ending 2: Salt & Musk</i>"]
    E3["<b>ending03_island_girl.md</b><br/><i>Ending 3: Island Girl</i>"]
    E4["<b>ending04_evidence_of_devotion.md</b><br/><i>Ending 4: Evidence of Devotion</i>"]
    E5["<b>ending05_happily_ever_after.md</b><br/><i>Ending 5: Happily Ever After</i>"]
    E6["<b>ending06_the_wolfs_den.md</b><br/><i>Ending 6: The Wolf's Den</i>"]
    E7["<b>ending07_evidence_and_instinct.md</b><br/><i>Ending 7: Evidence & Instinct</i>"]
    E8["<b>ending08_sovereign_and_sentinel.md</b><br/><i>Ending 8: Sovereign & Sentinel</i>"]
    E9["<b>ending09_the_vanguards_feast.md</b><br/><i>Ending 9: The Vanguard's Feast</i>"]

    %% CONNECTIVITY: TIER 1 -> TIER 2
    CH01 -->|"Stay behind with Makoto in the training hall"| CH02A
    CH01 -->|"Head to the communal bath with Kaori and Kasumi"| CH02B
    CH01 -->|"Follow Maho to her private chamber upstairs"| CH02C

    %% CONNECTIVITY: TIER 2 -> TIER 3
    CH02A -->|"Match her intensity — pin her against the training post"| CH03A1
    CH02A -->|"Step close into her guard — breathe in her heated skin"| CH03A2
    CH02A -->|"Answer Kasumi's knock at the archive pantry door"| CH03A3
    CH02A -->|"Welcome Maho into the moonlit kitchen"| CH03A4
    CH02A -->|"Let Kaori in from the bathhouse breezeway"| CH03A5

    CH02B -->|"Focus on Kaori — wade over to the shallow bench beside her"| CH03B1
    CH02B -->|"Focus on Kasumi — sit beside the detective at the rim"| CH03B2

    CH02C -->|"Play the prince in her courtly fairy tale"| CH03C1
    CH02C -->|"Leave the shoji ajar — let the pack hear the commotion"| CH03C2

    %% CONNECTIVITY: TIER 3 -> TIER 4
    CH03A1 -->|"Take the wolf on the mats"| CH04A1
    CH03A2 -->|"Part her thighs while pressed against her slick skin"| CH04A2
    CH03A3 -->|"Take them both on the kitchen floorboards"| CH04A3
    CH03A4 -->|"Surrender to the wild contest between wolf and fox"| CH04A4
    CH03A5 -->|"Test the two wild canines on the training mats"| CH04A5

    CH03B1 -->|"Push past her easygoing pace and take her deep"| CH04B1
    CH03B2 -->|"Shatter her deductive composure completely"| CH04B2

    CH03C1 -->|"Rewrite her fairy-tale climax with your own rhythm"| CH04C1
    CH03C2 -->|"Surrender to the entire pack's synchronized appetite"| CH04C2

    %% CONNECTIVITY: TIER 4 -> TIER 5 (ENDINGS)
    CH04A1 -->|"Hold the sleeping wolf close on the torn mats"| E1
    CH04A2 -->|"Slump against the kitchen floorboards in the quiet night"| E2
    CH04A3 -->|"Hold the twitching, cum-soaked detective and wolf close on the mats"| E7
    CH04A4 -->|"Rest in the tangled warmth of the exhausted wolf and fox"| E8
    CH04A5 -->|"Slump into the sweat-soaked mats between the sleeping hounds"| E9
    CH04B1 -->|"Carry the limp, smiling island girl to her bed"| E3
    CH04B2 -->|"Comfort the exhausted, blushing detective"| E4
    CH04C1 -->|"Tuck the fairy-tale princess under her silk quilt"| E5
    CH04C2 -->|"Greet the sunrise with the entire tangled pack"| E6
```

---

## 3. Chapter Ledger & Specifications

| Chapter File | Tier / Role | Minimum Words | NSFW Level | Key Beats & Off-Route Accounting |
|:---|:---:|:---:|:---:|:---|
| `ch01_sweat_and_steel.md` | Tier 1 (Root) | 1,500 | SFW | All 4 members sparring, cooling down, barley tea. 3-way branching choice. |
| `ch02a_the_wolfs_kitchen.md` | Tier 2A (Branch) | 1,500 | SFW $\to$ Tension | Makoto route anchor. 5-way branch: 2 solo, 3 threesomes (Kasumi, Maho, Kaori). |
| `ch02b_steam_and_stone.md` | Tier 2B (Branch) | 1,500 | SFW $\to$ Tension | Kaori/Kasumi route. Makoto stays in dojo, Maho upstairs. Bathhouse proximity. |
| `ch02c_the_foxs_chamber.md` | Tier 2C (Branch) | 1,500 | SFW $\to$ Tension | Maho route. Makoto/Kaori in dining hall, Kasumi in archives. Tea & fairy-tale room. |
| `ch03a1_fangs_and_claws.md` | Tier 3A1 (Foreplay) | 1,500 | Explicit Foreplay | Makoto rough: biting, pinning, oral, clawing, ears twitching. |
| `ch03a2_the_wolfs_musk.md` | Tier 3A2 (Foreplay) | 1,500 | Explicit Foreplay | Makoto musk: armpit licking, sweat worship, fingering, breast play. |
| `ch03a3_the_detectives_reprimand.md` | Tier 3A3 (Foreplay) | 1,500 | Explicit Foreplay | Makoto + Kasumi: bickering, audit interrupted, Doberman ear twitching, double oral. |
| `ch03a4_predator_and_vixen.md` | Tier 3A4 (Foreplay) | 1,500 | Explicit Foreplay | Makoto + Maho: predator vs vixen, plum nectar, competitive licking, tail-coiling. |
| `ch03a5_midnight_foragers.md` | Tier 3A5 (Foreplay) | 1,500 | Explicit Foreplay | Makoto + Kaori: hungry post-bath raid, dropped towel, double canine slobber oral. |
| `ch03b1_nankurunaisa.md` | Tier 3B1 (Foreplay) | 1,500 | Explicit Foreplay | Kaori bath: cheerful blowjob, wet clit massage, playful dirty talk. |
| `ch03b2_the_detectives_hypothesis.md` | Tier 3B2 (Foreplay) | 1,500 | Explicit Foreplay | Kasumi bath: clinical oral, steamed glasses, deductive composure cracking. |
| `ch03c1_once_upon_a_night.md` | Tier 3C1 (Foreplay) | 1,500 | Explicit Foreplay | Maho solo: fairy-tale narration, fox tail wrapping, refined dialect moans. |
| `ch03c2_the_packs_arrival.md` | Tier 3C2 (Foreplay) | 1,500 | Explicit Foreplay | Group assembly: Makoto, Kaori, Kasumi barge in; competitive strip & claims. |
| `ch04a1_alpha_claim.md` | Tier 4A1 (Climax) | 2,200 | Explicit Climax | Makoto rough: dominant riding, doggy, hair pulling, deep creampie. |
| `ch04a2_drenched.md` | Tier 4A2 (Climax) | 2,200 | Explicit Climax | Makoto sweat: armpit sex, drenched missionary, slippery creampie. |
| `ch04a3_interrogation_under_fire.md` | Tier 4A3 (Climax) | 2,200 | Explicit Climax | Makoto + Kasumi mind-break: petite stretching, shattered logic, ahegao, double creampie. |
| `ch04a4_crown_and_claw.md` | Tier 4A4 (Climax) | 2,200 | Explicit Climax | Makoto + Maho cognitive collapse: tail root stimulation, rolling eyes, double creampie. |
| `ch04a5_untamed_stamina.md` | Tier 4A5 (Climax) | 2,200 | Explicit Climax | Makoto + Kaori canine frenzy: broken nankurunaisa, excessive drool, double creampie. |
| `ch04b1_broken_mantra.md` | Tier 4B1 (Climax) | 2,200 | Explicit Climax | Kaori mind-break: ahegao, drool, broken "nankurunaisa", endless orgasms. |
| `ch04b2_case_closed.md` | Tier 4B2 (Climax) | 2,200 | Explicit Climax | Kasumi shattered: petite stretching, loud screams, detective unraveled. |
| `ch04c1_the_princes_conquest.md` | Tier 4C1 (Climax) | 2,200 | Explicit Climax | Maho ravished: tail coiling, Kyoto dialect shattered, fantasy climax. |
| `ch04c2_full_pack.md` | Tier 4C2 (Climax) | 2,200 | Explicit Climax | 5-way pack orgy: all 4 girls taken, multiple rounds, synchronized release. |
| `ending01_the_wolfs_mark.md` | Tier 5 (Ending 1) | 2,200 | Climax & Afterglow | Makoto aftermath: tavern breakfast, bite marks, pack teasing. |
| `ending02_salt_and_musk.md` | Tier 5 (Ending 2) | 2,200 | Climax & Afterglow | Makoto aftermath: warm bath cooldown, lingering scent, morning banter. |
| `ending03_island_girl.md` | Tier 5 (Ending 3) | 2,200 | Climax & Afterglow | Kaori aftermath: carrying her to futon, wobbly morning legs, sunny grins. |
| `ending04_evidence_of_devotion.md` | Tier 5 (Ending 4) | 2,200 | Climax & Afterglow | Kasumi aftermath: shaky case notes, morning analytical blushes. |
| `ending05_happily_ever_after.md` | Tier 5 (Ending 5) | 2,200 | Climax & Afterglow | Maho aftermath: morning tea, serene fox smile, tail clinging. |
| `ending06_the_wolfs_den.md` | Tier 5 (Ending 6) | 2,200 | Climax & Afterglow | Pack aftermath: tangled morning pile, shared clean-up, guild solidarity. |
| `ending07_evidence_and_instinct.md` | Tier 5 (Ending 7) | 2,200 | Climax & Afterglow | Makoto + Kasumi: archive morning, blotched incident report, breakfast melon. |
| `ending08_sovereign_and_sentinel.md` | Tier 5 (Ending 8) | 2,200 | Climax & Afterglow | Makoto + Maho: veranda breakfast, grilled river trout, knight-consort teasing. |
| `ending09_the_vanguards_feast.md` | Tier 5 (Ending 9) | 2,200 | Climax & Afterglow | Makoto + Kaori: kitchen cookout, crispy boar ribs, proud bruises, double run. |
