const fs=require("fs"); global.WormBrain=require("./brain.js").WormBrain; const P=require("./play.js");
const base=JSON.parse(fs.readFileSync("base.json")), p=JSON.parse(fs.readFileSync("params/pgx_bfree_k200.json")), T=JSON.parse(fs.readFileSync("test/free_bfree.json"));
const w=new P.WormPlayerJS(base,p); let worst=0;
T.senses.forEach((s,t)=>{ const keys=p.sense_keys,G=w.Win[0].length,xg=new Float32Array(G);
  for(let k=0;k<keys.length;k++){const v=Math.fround(s[keys[k]]||0); if(v) for(let g=0;g<G;g++) xg[g]=Math.fround(xg[g]+Math.fround(v*w.Win[k][g]));}
  const I=new Float32Array(w.brain.n); for(let j=0;j<w.in_idx.length;j++) I[w.in_idx[j]]=xg[w.in_group[j]];
  w.brain.step(I); p.actions.forEach((a,r)=>{let acc=0; for(let j=0;j<w.out_idx.length;j++) acc+=w.Wout[r][j]*w.brain.v[w.out_idx[j]]; worst=Math.max(worst,Math.abs(acc/w.out_idx.length*10-T.m[t][r]));});});
console.log("B translator+brain 150 steps, max motor diff", worst.toExponential(2), "| thresholds", p.readout);
