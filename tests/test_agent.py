import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from role_agent import Agent, ReplayBackend, Tools, ToolError, normalize, publish, load_persona

def decision(name,args):
    return json.dumps({'action':'tool','name':name,'args':args},ensure_ascii=False)

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=self.temp.name
        self.t=Tools(self.root)
    def tearDown(self):
        self.t.close(); self.temp.cleanup()
    def put(self):
        return self.t.execute('memory_put',{'key':'presentation','value':'週五，擔心設備','source':'user-msg-01'})
    def test_01_create_get(self):
        self.put(); self.assertEqual(self.t.execute('memory_get',{'key':'presentation'})['record']['value'],'週五，擔心設備')
    def test_02_restart_persistence(self):
        self.put(); other=Tools(self.root)
        try: self.assertTrue(other.execute('memory_get',{'key':'presentation'})['found'])
        finally: other.close()
    def test_03_correction_retains_history(self):
        self.put(); r=self.t.execute('memory_correct',{'key':'presentation','value':'週六','source':'user-msg-02','expected_version':1})
        self.assertEqual(r['record']['version'],2)
        self.assertEqual(self.t.db.execute('SELECT value FROM history').fetchone()[0],'週五，擔心設備')
    def test_04_stale_version_rejected(self):
        self.put()
        with self.assertRaisesRegex(ToolError,'VERSION_CONFLICT'):
            self.t.execute('memory_correct',{'key':'presentation','value':'週六','source':'m2','expected_version':0})
        self.assertEqual(self.t.execute('memory_get',{'key':'presentation'})['record']['version'],1)
    def test_05_unknown_is_not_invented(self):
        self.assertEqual(self.t.execute('memory_get',{'key':'unknown'}),{'found':False,'record':None})
    def test_06_role_isolation(self):
        self.put(); other=Tools(self.root,role='other')
        try: self.assertFalse(other.execute('memory_get',{'key':'presentation'})['found'])
        finally: other.close()
    def test_07_user_isolation(self):
        self.put(); other=Tools(self.root,user='other')
        try: self.assertFalse(other.execute('memory_get',{'key':'presentation'})['found'])
        finally: other.close()
    def test_08_duplicate_is_idempotent(self):
        self.put(); r=self.put(); self.assertTrue(r['unchanged']); self.assertEqual(r['record']['version'],1)
    def test_09_no_silent_overwrite(self):
        self.put()
        with self.assertRaisesRegex(ToolError,'KEY_EXISTS'):
            self.t.execute('memory_put',{'key':'presentation','value':'週六','source':'m2'})
    def test_10_invalid_scope(self):
        with self.assertRaisesRegex(ToolError,'INVALID_ID'): Tools(self.root,role='../secret')
    def test_11_scope_injection_rejected(self):
        with self.assertRaisesRegex(ToolError,'INVALID_ARGUMENTS'):
            self.t.execute('memory_get',{'key':'x','user':'other'})
    def test_12_search_literal(self):
        self.put(); self.assertEqual(len(self.t.execute('memory_search',{'query':'設備'})['matches']),1)
        self.assertEqual(self.t.execute('memory_search',{'query':"' OR 1=1 --"})['matches'],[])
    def test_13_delete_requires_confirmation(self):
        self.put()
        with self.assertRaisesRegex(ToolError,'CONFIRMATION_REQUIRED'):
            self.t.execute('memory_delete',{'key':'presentation','confirmed':False})
        self.assertTrue(self.t.execute('memory_get',{'key':'presentation'})['found'])
    def test_14_delete_purges_history(self):
        self.put(); self.t.execute('memory_correct',{'key':'presentation','value':'週六','source':'m2','expected_version':1})
        self.t.execute('memory_delete',{'key':'presentation','confirmed':True})
        self.assertEqual(self.t.db.execute('SELECT COUNT(*) FROM history').fetchone()[0],0)
    def test_15_normalization(self):
        records=json.loads((Path(__file__).resolve().parents[1]/'data/samples.json').read_text())
        r=normalize(records,'Aria'); self.assertEqual(len(r),2)
        self.assertTrue(all(x['speaker']=='Aria' and x['source']=='synthetic-01' for x in r))
    def test_16_bad_record(self):
        with self.assertRaisesRegex(ToolError,'INVALID_TEXT'):
            normalize([{'sender':'Aria','text':None}],'Aria')
    def test_17_publish_requires_review(self):
        with self.assertRaisesRegex(ToolError,'APPROVAL_REQUIRED'):
            publish({'name':'a','style':'b','samples':[]},self.root,'aria',False)
    def test_18_versioned_publication(self):
        a=publish({'name':'a','style':'short','samples':[]},self.root,'aria',True)
        b=publish({'name':'a','style':'direct','samples':[]},self.root,'aria',True)
        self.assertNotEqual(a['version'],b['version'])
        self.assertEqual(load_persona(self.root,'aria')['style'],'direct')
        self.assertTrue((Path(self.root)/'roles/aria'/(a['version']+'.json')).exists())
    def test_19_workflow_trace_fixture(self):
        self.put(); backend=ReplayBackend([decision('memory_get',{'key':'presentation'}),'{"action":"finish"}','你週五要展示 最擔心設備'])
        r=Agent(self.t,backend).run('我之前說展示是哪一天？')
        self.assertTrue(r['ok']); self.assertEqual([x['event'] for x in r['trace']],['input','decision','tool_call','observation','decision','final'])
    def test_20_bad_model_json(self):
        r=Agent(self.t,ReplayBackend(['not json'])).run('hi')
        self.assertFalse(r['ok']); self.assertEqual(r['trace'][-1]['code'],'INVALID_MODEL_JSON')
    def test_21_tool_step_limit(self):
        r=Agent(self.t,ReplayBackend([decision('memory_get',{'key':'x'})]*4)).run('hi')
        self.assertFalse(r['ok']); self.assertEqual(r['trace'][-1]['code'],'STEP_LIMIT')
    def test_22_unknown_tool_blocked(self):
        r=Agent(self.t,ReplayBackend([decision('shell_exec',{'cmd':'anything'})])).run('hi')
        self.assertFalse(r['ok']); self.assertEqual(r['trace'][-1]['code'],'INVALID_DECISION')
    def test_23_backend_failure(self):
        class Failed:
            def generate(self,prompt): raise ToolError('BACKEND_UNAVAILABLE_OR_TIMEOUT')
        r=Agent(self.t,Failed()).run('hi')
        self.assertFalse(r['ok']); self.assertEqual(r['trace'][-1]['code'],'BACKEND_UNAVAILABLE_OR_TIMEOUT')
    def test_24_error_observation_reaches_next_step(self):
        self.put()
        b=ReplayBackend([decision('memory_correct',{'key':'presentation','value':'六','source':'m2','expected_version':0}),'{"action":"finish"}','資料版本衝突 請重新讀取'])
        r=Agent(self.t,b).run('更正')
        self.assertEqual(r['trace'][3]['result']['error'],'VERSION_CONFLICT')
    def test_25_persona_tamper_detection(self):
        r=publish({'name':'a','style':'short','samples':[]},self.root,'aria',True)
        (Path(self.root)/'roles/aria'/(r['version']+'.json')).write_text('{}')
        with self.assertRaisesRegex(ToolError,'HASH_MISMATCH'): load_persona(self.root,'aria')

if __name__=='__main__': unittest.main(verbosity=2)
