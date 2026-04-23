# Sample Runs

The examples below are representative paths through the workflow. They show the state transitions and log shape this project is designed around.

## 1. Normal Pass

```text
Command:
python3 main.py --input demo_inputs/normal_task.txt

Path:
supervisor -> worker -> reviewer(pass, score=8.3) -> human_approval -> finalize

Resume:
python3 main.py --resume 2d9c6f3b --decision approve

Final status:
FINALIZED
```

## 2. Reviewer Fail Then Revision

```text
Command:
python3 main.py --input demo_inputs/revision_task.txt

Path:
supervisor -> worker -> reviewer(fail, score=4.7)
          -> worker(revision 1)
          -> reviewer(pass, score=7.4)
          -> human_approval
          -> finalize

Final status:
FINALIZED
```

## 3. Human Reject Then Re-Plan

```text
Command:
python3 main.py --input demo_inputs/human_review_task.txt

First pause:
python3 main.py --resume 78fb3218 --decision reject --reason "Tone is too technical for stakeholders"

Second path:
supervisor(re-plan with rejection reason) -> worker -> reviewer(pass)
-> human_approval -> finalize

Final approval:
python3 main.py --resume 78fb3218 --decision approve
```

## 4. Worker Error Then Recovery

```text
Command:
python3 main.py --request "SIMULATE_WORKER_TIMEOUT Create a launch checklist for a B2B analytics feature."

Path:
supervisor -> worker(timeout)
          -> error_handler(recoverable)
          -> supervisor(re-plan)
          -> worker
          -> reviewer(pass)
          -> human_approval
          -> finalize

Final status:
FINALIZED
```

## Example Execution Log

```text
1. [supervisor] 713ms
   Input:  Create a concise rollout plan for launching an internal AI writing assistant...
   Output: - Clarify rollout goals...
2. [worker (initial)] 1458ms
   Input:  Plan: - Clarify rollout goals...
   Output: 1. Goals ...
3. [reviewer] 926ms
   Output: pass (score=8.3/10): Draft is acceptable and can proceed.
4. [human_approval] 144ms
   Output: Decision: approve
5. [finalize] 611ms
   Output: Delivery Summary ...
```

