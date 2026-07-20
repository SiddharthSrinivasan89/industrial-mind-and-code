"""Serial local-ladder driver with 45/15 duty cycle. Run inside tmux with nohup.

Order per FROZEN-SPEC: per subject preflight -> Arm A -> Arm B; gpt-oss:120b additionally
Arm C probe + repeat diagnostics (primary subject). Any preflight FAIL stops that subject.
"""
import subprocess
import sys
import time

SUBJECTS = ["nemotron-3-super:120b"]  # STOP-AFTER-SUPER (Sid 2026-07-19); qwen3.5/qwen3:4b/nemotron-nano dropped
PRIMARY_EXTRAS = {"gpt-oss:120b": [("C", "probe"), ("A", "repeat")],
                  "nemotron-3-super:120b": [("C", "probe")]}  # repeats are diagnostics-only; dropped to save ~3.7h

run_started = time.time()
worked = 0.0


def duty_cycle():
    global worked, run_started
    if time.time() - run_started >= 45 * 60:
        print(f"[driver] 45min elapsed -> 15min cooldown", flush=True)
        time.sleep(15 * 60)
        run_started = time.time()


def step(subject, arm, events):
    print(f"[driver] {subject} arm {arm} events={events}", flush=True)
    r = subprocess.run([sys.executable, "code/run_subjects.py", "--subject", subject,
                        "--arm", arm, "--events", events])
    if r.returncode != 0:
        print(f"[driver] FAILED: {subject} arm {arm} {events} rc={r.returncode}", flush=True)
        return False
    duty_cycle()
    return True


for subject in SUBJECTS:
    if not step(subject, "A", "preflight"):
        print(f"[driver] preflight FAIL {subject} — skipping subject per SPEC", flush=True)
        continue
    for arm in ("A", "B"):
        if not step(subject, arm, "all"):
            break
    for arm, events in PRIMARY_EXTRAS.get(subject, []):
        step(subject, arm, events)
print("[driver] LADDER COMPLETE", flush=True)
