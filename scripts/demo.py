"""Real SQLite calls with SCRIPTED agent decisions/replies; not live LLM evidence."""
from pathlib import Path
import sys,json,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from role_agent import Agent,Tools,ReplayBackend

def call(name,args): return json.dumps({'action':'tool','name':name,'args':args},ensure_ascii=False)
finish='{"action":"finish"}'
scenarios=[
 ('write','幫我記住週五要展示 我最擔心設備出錯',[call('memory_put',{'key':'presentation','value':'週五展示；擔心設備出錯','source':'synthetic-user-01'}),finish,'好 週五展示 你擔心的是設備']),
 ('recall','我之前說展示是哪天 最擔心什麼',[call('memory_get',{'key':'presentation'}),finish,'週五 你最擔心設備出錯']),
 ('correct','展示改週六了',[call('memory_get',{'key':'presentation'}),call('memory_correct',{'key':'presentation','value':'週六展示；擔心設備出錯','source':'synthetic-user-03','expected_version':1}),finish,'改成週六了']),
 ('unknown','我沒說過的餐廳名字是什麼',[call('memory_get',{'key':'restaurant'}),finish,'這個我沒有紀錄 你之前還沒告訴我']),
 ('invalid_json','測試格式錯誤',['not json']),
 ('stale_update','測試舊版本更正',[call('memory_correct',{'key':'presentation','value':'週日','source':'synthetic-user-06','expected_version':1}),finish,'版本衝突 先重新讀取再更正'])
]
with tempfile.TemporaryDirectory() as root:
    t=Tools(root)
    results=[]
    for name,message,responses in scenarios:
        results.append({'scenario':name,**Agent(t,ReplayBackend(responses)).run(message)})
    t.close()
print(json.dumps({'evidence_type':'SCRIPTED_BACKEND_REAL_SQLITE','live_llm':False,'scenarios':results},ensure_ascii=False,indent=2))
