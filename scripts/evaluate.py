"""Small reproducible lexical/semantic-fallback/hybrid retrieval evaluation."""
import json, math, re, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=json.loads((ROOT/'evaluation/dataset.json').read_text(encoding='utf-8'))

def tokens(s): return set(re.findall(r"[a-z0-9+#.]+",s.lower()))
def lexical(q,j): return len(tokens(q)&tokens(j['title']+' '+j['description']+' '+' '.join(j['required_skills'])))
def semantic_fallback(q,j):
    # Transparent token-overlap fallback. It is not a sentence embedding model.
    return len(tokens(q)&tokens(j['title']+' '+j['description']+' '+' '.join(j['required_skills'])))/max(1,len(tokens(q)))
def ranked(q,method):
    score=(lexical if method=='lexical' else semantic_fallback)
    return [j['id'] for j in sorted(DATA['jobs'],key=lambda j:(-score(q['query'],j),j['id']))]
def dcg(rels): return sum((2**r-1)/math.log2(i+2) for i,r in enumerate(rels))
def metrics(order,relevant,k=3):
    rel=[1 if x in relevant else 0 for x in order[:k]]
    hits=sum(rel); first=next((i+1 for i,x in enumerate(order) if x in relevant),None)
    ideal=sorted([1]*min(k,len(relevant))+[0]*k,reverse=True)[:k]
    return {'precision_at_3':hits/k,'recall_at_3':hits/max(1,len(relevant)),'mrr':1/first if first else 0,'ndcg_at_3':dcg(rel)/max(1e-12,dcg(ideal))}
def main():
    output={'dataset_label':DATA['label'],'judgments':len(DATA['queries']),'strategies':{},'note':'Semantic mode is a documented lexical-overlap fallback; no embedding model was run.'}
    for method in ['lexical','semantic_fallback','hybrid']:
        values=[]
        for q in DATA['queries']:
            if method=='hybrid':
                a=ranked(q,'lexical'); b=ranked(q,'semantic_fallback'); fused={}
                for ranking in [a,b]:
                    for rank,key in enumerate(ranking,1): fused[key]=fused.get(key,0)+1/(60+rank)
                order=[key for key,_ in sorted(fused.items(),key=lambda x:(-x[1],x[0]))]
            else: order=ranked(q,'lexical' if method=='lexical' else 'semantic')
            values.append(metrics(order,q['relevant']))
        output['strategies'][method]={k:round(sum(x[k] for x in values)/len(values),4) for k in values[0]}
    path=ROOT/'reports';path.mkdir(exist_ok=True);(path/'retrieval-evaluation.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
    lines=['# Retrieval evaluation','',f"Dataset: {output['dataset_label']} ({output['judgments']} synthetic queries)",'','Scores are measured by `python scripts/evaluate.py`. Semantic fallback is lexical token overlap, not embeddings.','', '| Strategy | P@3 | Recall@3 | MRR | nDCG@3 |','|---|---:|---:|---:|---:|']
    for name,m in output['strategies'].items(): lines.append(f"| {name} | {m['precision_at_3']:.4f} | {m['recall_at_3']:.4f} | {m['mrr']:.4f} | {m['ndcg_at_3']:.4f} |")
    (path/'retrieval-evaluation.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');print(json.dumps(output,indent=2))
if __name__=='__main__':main()
