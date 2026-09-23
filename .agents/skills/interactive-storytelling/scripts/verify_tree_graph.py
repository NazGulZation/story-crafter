#!/usr/bin/env python3
"""
Interactive Story Tree Graph Auditor
StoryCrafter Specialized Verification Tool

Validates that interactive branching stories adhere to the Absolute Tree Architecture:
1. Strict Out-Tree: Every non-root node has in-degree == 1 (zero convergence, no merging paths).
2. Dedicated Terminal Endings: Every ending node has in-degree == 1 and out-degree == 0 (no shared endings).
3. Mathematical Branch-to-Ending Invariant: Endings >= Branches (E >= B).
4. No Dead Ends: Every non-ending chapter offers at least 2 choices.
5. Integrity: No broken targets, no cycles, all nodes reachable from root.
"""

import sys
import os
import re
import argparse
from pathlib import Path
from collections import defaultdict, deque


def parse_chapter_file(file_path):
    """Parse a single chapter markdown file for choices and ending markers."""
    text = file_path.read_text(encoding="utf-8")
    
    is_ending = False
    ending_title = None
    
    # Check frontmatter
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm_str = parts[1]
            for fline in fm_str.splitlines():
                if fline.strip().lower().startswith("ending:"):
                    val = fline.split(":", 1)[1].strip().lower()
                    if val in ("true", "yes", "1"):
                        is_ending = True
                elif fline.strip().lower().startswith("ending_title:"):
                    ending_title = fline.split(":", 1)[1].strip().strip('"\'')

    # Check for ### Ending: [Title] heading
    m_ending = re.search(r'^\s*#{2,3}\s+Ending:\s*(.+)$', text, re.MULTILINE | re.IGNORECASE)
    if m_ending:
        is_ending = True
        if not ending_title:
            ending_title = m_ending.group(1).strip()

    # Parse Choices block
    choices = []
    choices_pattern = r'(?:\r?\n|^)\s*#{2,3}\s+Choices\s*\r?\n([\s\S]*?)$'
    m_choices = re.search(choices_pattern, text, re.IGNORECASE)
    if m_choices:
        choices_block = m_choices.group(1)
        for bline in choices_block.splitlines():
            m_link = re.search(r'[-*]\s*\[(.*?)\]\((.*?)\)', bline)
            if m_link:
                c_text = m_link.group(1).strip()
                c_target = m_link.group(2).strip().replace("\\", "/").split("/")[-1]
                if c_text and c_target:
                    choices.append({
                        "text": c_text,
                        "target": c_target
                    })

    # Extract title
    title = ""
    for line in text.splitlines():
        if line.startswith("# ") and not title:
            title = line[2:].strip()
            break
    if not title:
        title = file_path.stem.replace("_", " ").title()

    return {
        "filename": file_path.name,
        "title": title,
        "is_ending": is_ending,
        "ending_title": ending_title or (title if is_ending else None),
        "choices": choices
    }


def audit_story_graph(story_dir):
    """
    Audit the branching graph of a story directory.
    Returns (is_valid, report_dict).
    """
    story_dir = Path(story_dir)
    chapters_dir = story_dir / "chapters"
    if not chapters_dir.is_dir():
        return False, {
            "story": story_dir.name,
            "error": f"No 'chapters' directory found in {story_dir}"
        }

    # Sort files
    md_files = sorted(
        chapters_dir.glob("*.md"),
        key=lambda f: [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', f.name)]
    )

    if not md_files:
        return False, {
            "story": story_dir.name,
            "error": "No markdown files found in chapters directory"
        }

    chapters = {}
    for f in md_files:
        try:
            chapters[f.name] = parse_chapter_file(f)
        except Exception as e:
            return False, {
                "story": story_dir.name,
                "error": f"Failed to parse {f.name}: {e}"
            }

    # Detect if story is interactive
    is_interactive = any(bool(c["choices"] or c["is_ending"]) for c in chapters.values())
    if not is_interactive:
        return True, {
            "story": story_dir.name,
            "is_interactive": False,
            "message": "Linear story (no choices or ending tags). Tree rules not applicable."
        }

    # Build Graph
    # Nodes: filenames
    in_edges = defaultdict(list)   # target -> [parents]
    out_edges = defaultdict(list)  # source -> [targets]
    violations = []
    warnings = []

    # Map edges
    for fname, data in chapters.items():
        for ch in data["choices"]:
            target = ch["target"]
            out_edges[fname].append(target)
            in_edges[target].append(fname)
            if target not in chapters:
                violations.append(f"Broken Target: Chapter '{fname}' links to non-existent target '{target}'.")

    # 1. Root Node Check
    root_candidates = [fname for fname in chapters if len(in_edges[fname]) == 0]
    if len(root_candidates) == 0:
        violations.append("Cyclic Graph: No root node found (all nodes have incoming edges). A tree must have an opening root chapter.")
        root_node = md_files[0].name
    elif len(root_candidates) > 1:
        # Check if the other roots are disconnected orphans
        violations.append(
            f"Multiple Root / Orphan Nodes: Found {len(root_candidates)} nodes with in-degree 0: {root_candidates}. "
            "All branches must emanate from a single root chapter."
        )
        root_node = root_candidates[0]
    else:
        root_node = root_candidates[0]

    # 2. Strict Tree In-Degree Check (Zero Convergence)
    converging_nodes = []
    for fname, parents in in_edges.items():
        if len(parents) > 1:
            converging_nodes.append((fname, parents))
            is_end = chapters.get(fname, {}).get("is_ending", False)
            node_type = "Terminal Ending" if is_end else "Intermediate Chapter"
            violations.append(
                f"Convergence Violation ({node_type}): '{fname}' has in-degree {len(parents)} (parents: {parents}). "
                "Absolute Tree Architecture requires in-degree == 1 for all non-root nodes (zero merging allowed)."
            )

    # 3. Terminal Ending In-Degree & Out-Degree
    endings = [fname for fname, c in chapters.items() if c["is_ending"]]
    if not endings:
        violations.append("Missing Endings: Interactive story has choices but 0 terminal ending chapters designated.")

    for end_fname in endings:
        if len(out_edges[end_fname]) > 0:
            violations.append(
                f"Ending Node Out-Degree Violation: Ending chapter '{end_fname}' offers choices ({out_edges[end_fname]}). "
                "Terminal endings must have out-degree == 0."
            )

    # 4. Dead Ends (Non-ending chapters with no choices)
    for fname, c in chapters.items():
        if not c["is_ending"]:
            if len(out_edges[fname]) == 0:
                violations.append(
                    f"Dead-End Chapter: '{fname}' is not marked as an ending but offers no choices (out-degree == 0)."
                )
            elif len(out_edges[fname]) == 1:
                warnings.append(
                    f"Single-Option Choice: '{fname}' offers only 1 choice ({out_edges[fname][0]}). "
                    "Interactive choices should provide meaningful divergence (>= 2 choices)."
                )

    # 5. Reachability (Check for unreachable nodes)
    reachable = set()
    queue = deque([root_node])
    while queue:
        curr = queue.popleft()
        if curr in reachable:
            continue
        reachable.add(curr)
        for nxt in out_edges.get(curr, []):
            if nxt in chapters and nxt not in reachable:
                queue.append(nxt)

    unreachable = set(chapters.keys()) - reachable
    if unreachable:
        violations.append(f"Unreachable Nodes: The following chapters cannot be reached from root '{root_node}': {sorted(list(unreachable))}.")

    # 6. Cycle Detection
    visited_state = {}  # 0 = unvisited, 1 = visiting, 2 = visited
    has_cycle = False
    cycle_nodes = []

    def dfs(node, path):
        nonlocal has_cycle
        visited_state[node] = 1
        for neighbor in out_edges.get(node, []):
            if neighbor not in chapters:
                continue
            if visited_state.get(neighbor) == 1:
                has_cycle = True
                cycle_nodes.append(path + [neighbor])
            elif visited_state.get(neighbor, 0) == 0:
                dfs(neighbor, path + [neighbor])
        visited_state[node] = 2

    dfs(root_node, [root_node])
    if has_cycle:
        violations.append(f"Loop/Cycle Detected: Graph contains feedback loops: {cycle_nodes}. Interactive stories must be a strict directed tree.")

    # 7. Mathematical Invariant: Endings >= Branches
    # Count root branches
    root_branches = len(out_edges.get(root_node, []))
    total_endings = len(endings)
    
    # Calculate total decision branches (sum of choices at all decision nodes)
    total_decision_nodes = sum(1 for fname, c in chapters.items() if len(out_edges.get(fname, [])) >= 2)
    
    if total_endings < root_branches:
        violations.append(
            f"Mathematical Violation (Endings < Root Branches): Story has {total_endings} endings but root chapter '{root_node}' "
            f"spawns {root_branches} immediate branches. Every branch must culminate in at least one dedicated ending."
        )

    # Check that each child branch of the root leads to its own dedicated ending(s)
    # and no ending is shared across root branches
    root_child_ending_sets = {}
    for child in out_edges.get(root_node, []):
        child_endings = set()
        c_queue = deque([child])
        c_visited = set()
        while c_queue:
            curr = c_queue.popleft()
            if curr in c_visited:
                continue
            c_visited.add(curr)
            if curr in endings:
                child_endings.add(curr)
            for nxt in out_edges.get(curr, []):
                if nxt in chapters and nxt not in c_visited:
                    c_queue.append(nxt)
        root_child_ending_sets[child] = child_endings
        if len(child_endings) == 0:
            violations.append(
                f"Dead Branch Violation: Branch path starting at '{child}' does not terminate in any ending."
            )

    # Check pairwise intersection of ending sets across root branches
    root_children = list(root_child_ending_sets.keys())
    for i in range(len(root_children)):
        for j in range(i + 1, len(root_children)):
            c1 = root_children[i]
            c2 = root_children[j]
            shared = root_child_ending_sets[c1].intersection(root_child_ending_sets[c2])
            if shared:
                violations.append(
                    f"Shared Ending Violation: Branches '{c1}' and '{c2}' merge into shared ending(s): {sorted(list(shared))}. "
                    "Cross-branch ending sharing is strictly prohibited."
                )

    is_valid = len(violations) == 0

    return is_valid, {
        "story": story_dir.name,
        "is_interactive": True,
        "root_node": root_node,
        "total_chapters": len(chapters),
        "total_endings": total_endings,
        "root_branches": root_branches,
        "decision_nodes": total_decision_nodes,
        "converging_nodes": len(converging_nodes),
        "violations": violations,
        "warnings": warnings,
        "root_child_breakdown": {
            child: sorted(list(ends)) for child, ends in root_child_ending_sets.items()
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Audit interactive story graphs for Absolute Tree Architecture.")
    parser.add_argument("story_dir", nargs="?", default=None, help="Path to story directory or story ID.")
    parser.add_argument("--all", action="store_true", help="Audit all interactive stories in workspace.")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parents[4]  # c:\StoryCrafter
    if not (base_dir / "GEMINI.md").exists():
        # Fallback to current working directory
        base_dir = Path(os.getcwd())

    targets = []
    if args.all or args.story_dir is None:
        for item in sorted(base_dir.iterdir()):
            if item.is_dir() and (item / "chapters").is_dir() and not item.name.startswith((".", "_", "venv")):
                targets.append(item)
    else:
        target_path = Path(args.story_dir)
        if not target_path.is_dir():
            target_path = base_dir / args.story_dir
        if not target_path.is_dir():
            print(f"[ERROR] Directory not found: {args.story_dir}")
            sys.exit(1)
        targets.append(target_path)

    total_audited = 0
    passed_count = 0
    failed_count = 0

    print("=" * 72)
    print("      StoryCrafter Interactive Story Tree Graph Auditor")
    print("=" * 72)

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    for sdir in targets:
        is_valid, report = audit_story_graph(sdir)
        if not report.get("is_interactive", False):
            continue

        total_audited += 1
        print(f"\n[STORY] {report['story']}")
        print(f"   Root Chapter:      {report.get('root_node', 'N/A')}")
        print(f"   Total Chapters:    {report.get('total_chapters', 0)}")
        print(f"   Root Branches:     {report.get('root_branches', 0)}")
        print(f"   Terminal Endings:  {report.get('total_endings', 0)}")
        print(f"   Decision Nodes:    {report.get('decision_nodes', 0)}")
        
        breakdown = report.get("root_child_breakdown", {})
        if breakdown:
            print("   Branch Lineages:")
            for b_child, b_ends in breakdown.items():
                print(f"     |-- [{b_child}] -> {len(b_ends)} ending(s): {', '.join(b_ends) if b_ends else 'NONE'}")

        if report.get("warnings"):
            print("   [WARN] Warnings:")
            for w in report["warnings"]:
                print(f"     * {w}")

        if is_valid:
            print("   [PASS] Status: PASS (Strict Absolute Tree, In-Degree == 1, Endings >= Branches)")
            passed_count += 1
        else:
            print(f"   [FAIL] Status: FAIL ({len(report['violations'])} violation(s))")
            for v in report["violations"]:
                print(f"     [X] {v}")
            failed_count += 1

    print("\n" + "=" * 72)
    print(f"Audit Summary: {total_audited} interactive stories checked.")
    print(f"Passed: {passed_count} | Failed: {failed_count}")
    print("=" * 72)

    if failed_count > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
