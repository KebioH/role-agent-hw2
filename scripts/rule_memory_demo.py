"""Run the actual HW2 Agent + SQLite with a local command-based decision backend."""
from pathlib import Path
import hashlib
import json
import re
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from role_agent import Agent, Tools

class RuleBackend:
    def generate(self, prompt):
        header, payload = prompt.split('\n', 1)
        context = json.loads(payload)
        message = context['message']
        match = re.fullmatch(r'(記住|更正|查詢)\s+([^：:\n]+)(?:[：:]\s*(.+))?', message)
        good = match and bool(match[3]) == (match[1] != '查詢')
        ops = context['observations']
        last = ops[-1]['result'] if ops else {}
        rec = last.get('record')
        if 'tools' not in context:
            if not good:
                return '格式：記住／更正 主題：內容，或查詢 主題。'
            if 'error' in last:
                return f"操作失敗：{last['error']}"
            if not rec:
                return '沒有這筆記憶。'
            return ('已記住：' if match[1]=='記住' else '已更正：' if match[1]=='更正' else '') + rec['value']
        decision = {'action':'finish'}
        if good:
            op, key, value = match.groups()
            key = key.strip()
            source = 'rule-' + hashlib.sha256(message.encode()).hexdigest()[:12]
            call = None
            if not ops:
                call = ('memory_put',dict(key=key,value=value,source=source)) if op=='記住' else ('memory_get',dict(key=key))
            elif op=='更正' and len(ops)==1 and ops[0]['tool']=='memory_get' and rec:
                call = ('memory_correct',dict(key=key,value=value,source=source,expected_version=rec['version']))
            if call:
                decision = dict(action='tool',name=call[0],args=call[1])
        return json.dumps(decision,ensure_ascii=False)

def main():
    key, initial, changed = sys.argv[1:] if len(sys.argv)==4 else ('策展彩排','週三下午兩點，記得帶轉接頭','週四上午十點，記得帶轉接頭')
    messages = [f'記住 {key}：{initial}',f'查詢 {key}',f'更正 {key}：{changed}',f'查詢 {key}',f'查詢 {key}未登錄']
    with tempfile.TemporaryDirectory() as db:
        outputs=[]
        for message in messages:
            tools=Tools(db)
            try:
                outputs.append(Agent(tools,RuleBackend()).run(message))
            finally:
                tools.close()
        assert all(r['ok'] for r in outputs)
        assert outputs[1]['reply']==initial and outputs[3]['reply']==changed
        assert outputs[4]['reply']=='沒有這筆記憶。'
        calls=[e['name'] for e in outputs[2]['trace'] if e['event']=='tool_call']
        assert calls==['memory_get','memory_correct']
        obs=[e['result'] for e in outputs[2]['trace'] if e['event']=='observation']
        assert [o['record']['version'] for o in obs]==[1,2]
    print(json.dumps({'evidence_type':'RULE_BACKEND_REAL_SQLITE','live_llm':False,'runs':outputs},ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
