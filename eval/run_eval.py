"""Score fixed self-authored expectations; never derive labels from the implementation."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from datetime import datetime
from zoneinfo import ZoneInfo
import yaml
from app.main import make_ticket
from app.llm.mock import MockProvider
from app.guard import violations
NOW=datetime(2026,10,8,12,tzinfo=ZoneInfo('America/New_York'))
def lookup(obj,path):
    for key in path.split('.'):
        obj=obj[int(key)] if isinstance(obj,list) else obj[key]
    return obj
def run():
    cases=yaml.safe_load(Path('tests/cases.yaml').read_text())
    correct=total=tp=fp=fn=bad=0; failures=[]
    for case in cases:
        ticket=make_ticket(case['message'],NOW,MockProvider())
        data=ticket.extraction.model_dump(mode='json')
        for field,expected in case['expected_fields'].items():
            total+=1
            try:actual=lookup(data,field)
            except (KeyError,IndexError):actual='<missing>'
            correct+=actual==expected
            if actual!=expected:failures.append(f"Case {case['id']}: {field}: expected {expected!r}, got {actual!r}")
        actual=set(ticket.handoff_reasons);expected=set(case['expected_handoff_reasons'])
        tp+=len(actual&expected);fp+=len(actual-expected);fn+=len(expected-actual)
        if actual!=expected:failures.append(f"Case {case['id']}: extra {sorted(actual-expected)}, missing {sorted(expected-actual)}")
        bad+=bool(violations(ticket.customer_reply) or any(p in ticket.customer_reply.lower() for p in case['must_not_contain']))
    report=f'''# Intake evaluation

Self-authored; not real customer data. n={len(cases)} fictional cases. Provider: deterministic mock. Fixed time: {NOW.isoformat()}.

| Metric | Result | Computation |
| --- | --- | --- |
| Field extraction accuracy | {correct/total:.1%} | {correct}/{total} explicitly annotated field checks match exactly; unannotated fields are not scored |
| Handoff precision | {tp/(tp+fp):.1%} | {tp} true positives / {tp+fp} predicted reasons, micro-averaged |
| Handoff recall | {tp/(tp+fn):.1%} | {tp} true positives / {tp+fn} expected reasons, micro-averaged |
| Forbidden-claim violations | {bad} | Number of replies failing deterministic scanner or per-case forbidden phrases; target zero |

This small test set measures these authored examples only. It does not establish real-world accuracy. Mock results do not measure a live LLM. Template allowlisting prevents arbitrary output claims; regex scanning alone is not a complete semantic safety test.

## Mismatches

'''+ ('\n'.join('- '+f for f in failures) if failures else 'None.')+'\n'
    Path('eval/report.md').write_text(report)
    print(report)
    return failures,bad
if __name__=='__main__':
    failures,bad=run()
    sys.exit(bool(failures or bad))
