"""Offline replay of published responses and statistics; no API keys or paid calls."""
import ast, argparse, collections, hashlib, itertools, json, logging, random, re, statistics, traceback
from pathlib import Path
from types import SimpleNamespace
from typing import Any
ROOT=Path(__file__).resolve().parent
MODELS=tuple(json.loads((ROOT/'provenance.json').read_text())['models'])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def metric(items):
 return {'correct':sum(x['correct'] for x in items),'total':len(items),'accuracy':sum(x['correct'] for x in items)/len(items),'outcomes':dict(collections.Counter(x['outcome'] for x in items))}

def bootstrap(records,models,draws=10000,seed=20261014):
 rng=random.Random(seed);assets=sorted({r['asset_name'] for r in records});pairs=[]
 bymodel={m:{r['id']:r for r in records if r['model']==m} for m in models}
 ids=sorted(bymodel[models[0]])
 assert all(set(bymodel[m])==set(ids) for m in models)
 for a,b in itertools.combinations(models,2):
  clusters=[(sum(int(bymodel[a][i]['correct'])-int(bymodel[b][i]['correct']) for i in ids if bymodel[a][i]['asset_name']==asset),sum(bymodel[a][i]['asset_name']==asset for i in ids)) for asset in assets]
  samples=[]
  for _ in range(draws):
   draw=[rng.choice(clusters) for _ in assets];samples.append(sum(v[0] for v in draw)/sum(v[1] for v in draw))
  samples.sort();pairs.append({'a':a,'b':b,'difference':sum(int(bymodel[a][i]['correct'])-int(bymodel[b][i]['correct']) for i in ids)/len(ids),'descriptive_asset_resampling_95_interval':[samples[int(draws*.025)-1],samples[int(draws*.975)-1]],'a_only_correct':sum(bymodel[a][i]['correct'] and not bymodel[b][i]['correct'] for i in ids),'b_only_correct':sum(bymodel[b][i]['correct'] and not bymodel[a][i]['correct'] for i in ids)})
 return pairs

def usage(raw,model):
    u=raw.get('usage',{})
    if model=='gpt-6.1-sol':
        inp=u.get('input_tokens',0);cached=u.get('input_tokens_details',{}).get('cached_tokens',0);write=u.get('input_tokens_details',{}).get('cache_creation_tokens',0)
        output=u.get('output_tokens',0);reason=u.get('output_tokens_details',{}).get('reasoning_tokens',0)
        cost=((inp-cached-write)*2+cached*.1+write*2.5+output*10)/1e6
    else:
        inp=u.get('total_input_tokens',0);cached=u.get('total_cached_tokens',0);reason=u.get('total_thought_tokens',0);output=u.get('total_output_tokens',0)+reason
        ir,orr={'gemini-3.8-flash':(.75,3.75),'gemini-3.1-pro-preview':(2,12),'gemini-4-argon':(2,10)}[model]
        if model=='gemini-3.1-pro-preview' and inp>200000:ir,orr=4,18
        # Explicit Google caching was not requested; cached token pricing is documented separately.
        assert cached==0,'Unexpected cached Gemini usage; verify applicable rates before costing'
        cost=(inp*ir+output*orr)/1e6
    assert u and inp>=0 and output>=0,'Missing usage'
    return {'input':inp,'output_including_reasoning':output,'reasoning':reason,'cached':cached,'cost_usd':cost}

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--dataset',type=Path,required=True);parser.add_argument('--ibm-source',type=Path,required=True);args=parser.parse_args()
 source=json.loads((ROOT/'provenance.json').read_text());assert sha(args.dataset)==source['dataset']['sha256'];assert sha(args.ibm_source)==source['ibm_source_sha256']
 tree=ast.parse(args.ibm_source.read_text());renderer=next(m for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='MultipleChoiceQuestion' for m in n.body if isinstance(m,ast.FunctionDef) and m.name=='get_prompt');funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('fix_json_string','get_mcq_llm_answer')]
 ns={'List':list,'Optional':Any,'MultipleChoiceQuestion':Any,'LargeLanguageModel':Any,'random':random,'logging':logging,'traceback':traceback,'re':re,'json':json};exec(compile(ast.Module(body=[renderer]+funcs,type_ignores=[]),'<pinned native IBM helpers>','exec'),ns)
 data={r['id']:r for r in map(json.loads,args.dataset.read_text().splitlines())};items=json.loads((ROOT/'item-scores.json').read_text());byitem={(r['model'],r['id']):r for r in items};records=[json.loads(line) for line in (ROOT/'responses.jsonl').read_text().splitlines()];assert len(byitem)==len(items)==len(records)==702
 costs=collections.Counter();latencies={m:[] for m in MODELS}
 for record in records:
  row=data[record['id']];item=byitem[record['model'],record['id']];q=SimpleNamespace(**{k:row[k] for k in ['question','options','option_ids','question_first','text_type','correct']},trigger_statement=source['native_trigger']);q.get_prompt=lambda:ns['get_prompt'](q)
  class Replay:
   def refresh(self):self.i=0
   def listen_and_response(self,prompt):
    turn=record['turns'][self.i];self.i+=1;return turn['response_text']
  replay=Replay();predicted,text=ns['get_mcq_llm_answer'](q,replay);assert replay.i==len(record['turns']);assert predicted==item['prediction'] and item['gold']==row['correct'];assert item['correct']==(predicted==row['correct'])
  elapsed=0
  for turn in record['turns']:
   assert turn['provider_reported_model'] in (record['model'],record['model']+'-2026-09-29')
   costs[record['model']]+=usage({'usage':turn['usage']},record['model'])['cost_usd'];elapsed+=turn['elapsed_seconds']
  latencies[record['model']].append(elapsed)
 analysis=json.loads((ROOT/'analysis.json').read_text());shared=set.intersection(*[{r['id'] for r in items if r['model']==m} for m in MODELS]);assert shared==set(source['shared_question_ids'])
 paired=[r for r in items if r['id'] in shared];assert len(paired)==680
 for m in MODELS:
  assert metric([r for r in paired if r['model']==m])==analysis['primary_scores'][m]
  assert abs(costs[m]-analysis['operations_all_completed'][m]['successful_list_cost_usd'])<1e-12
  assert statistics.median(latencies[m])==analysis['operations_all_completed'][m]['latency_median_seconds']
 assert bootstrap(paired,MODELS)==analysis['paired_differences']
 print(json.dumps({'replayed_responses':702,'matched_questions_per_model':len(shared),'primary_scores':analysis['primary_scores'],'all6paired_statistics':'MATCH','usage_costs_and_medians':'MATCH'},indent=2))
if __name__=='__main__':main()
