"""Frozen parse policy (FROZEN-SPEC v5 §13). Single pass, string/escape-aware, no repair."""
import json


def _fence_strip(text):
    return "\n".join(l for l in text.split("\n") if not l.strip().startswith("```"))


def _balanced_blocks(text):
    """All balanced top-level {...} blocks; braces inside JSON string literals ignored."""
    blocks, depth, start, in_str, esc = [], 0, None, False, False
    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"' and depth > 0:
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0:
                blocks.append(text[start : i + 1])
    return blocks


def parse_component(text, presented_labels):
    """Returns (label_or_None, parse_status)."""
    if not text or not text.strip():
        return None, "fallback"
    norm = {l.strip().casefold(): l for l in presented_labels}
    for block in _balanced_blocks(_fence_strip(text)):
        try:
            obj = json.loads(block)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(obj, dict) or "component" not in obj:
            continue
        val = obj["component"]
        if isinstance(val, str) and val.strip().casefold() in norm:
            return norm[val.strip().casefold()], "ok"
        return None, "fallback"  # component key present but invalid value
    return None, "fallback"


GOLDEN = [
    # (input, presented, expected_label, expected_status)
    ('{"component": "comp2"}', ["comp1", "comp2", "comp3", "comp4"], "comp2", "ok"),
    ('```json\n{"component": "comp3", "rationale": "x"}\n```', ["comp1", "comp2", "comp3", "comp4"], "comp3", "ok"),
    ('Stats: {mean: 10.5} suggest wear.\n{"component": "comp1"}', ["comp1", "comp2", "comp3", "comp4"], "comp1", "ok"),
    ('{"component": "comp4", "rationale": "braces {x} and \\" quote"}', ["comp1", "comp2", "comp3", "comp4"], "comp4", "ok"),
    ('{"component": " Comp2 "}', ["comp1", "comp2", "comp3", "comp4"], "comp2", "ok"),
    ('```\n{"note": 1}\n```\n```\n{"component": "unitB"}\n```', ["unitA", "unitB", "unitC", "unitD"], "unitB", "ok"),
    ("I think it is component 2.", ["comp1", "comp2", "comp3", "comp4"], None, "fallback"),
    ('{"component": "comp2"}', ["unitA", "unitB", "unitC", "unitD"], None, "fallback"),
    ('{"component": ["comp2"]}', ["comp1", "comp2", "comp3", "comp4"], None, "fallback"),
    ("", ["comp1", "comp2", "comp3", "comp4"], None, "fallback"),
]


def self_test():
    for i, (txt, labels, want_label, want_status) in enumerate(GOLDEN):
        got, status = parse_component(txt, labels)
        assert (got, status) == (want_label, want_status), f"golden {i}: got {(got, status)}"
    return len(GOLDEN)


if __name__ == "__main__":
    print(f"parse_policy self-test: {self_test()}/{len(GOLDEN)} golden cases pass")
