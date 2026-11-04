// node brain.test.cjs [run]: replays the Python test inputs and compares neuron states step by step
const fs = require("fs"), { WormBrain } = require("./brain.js");
const run = process.argv[2] || "pgx_freefire";
const base = JSON.parse(fs.readFileSync(__dirname + "/base.json"));
const p = JSON.parse(fs.readFileSync(`${__dirname}/params/${run}.json`));
const T = JSON.parse(fs.readFileSync(`${__dirname}/test/${run}.json`));
const b = new WormBrain(base, p);
let worst = 0, worstM = 0;
const t0 = Date.now();
T.inputs.forEach((inp, t) => {
  const m = b.step(inp);
  let d = 0; for (let i = 0; i < b.n; i++) d = Math.max(d, Math.abs(b.v[i] - T.v[t][i]));
  worst = Math.max(worst, d);
  for (const k in m) worstM = Math.max(worstM, Math.abs(m[k] - T.motors[t][k]));
});
const ms = (Date.now() - t0) / T.inputs.length;
console.log(`${run}: ${T.inputs.length} steps, max |v diff| ${worst.toExponential(2)}, max motor diff ${worstM.toExponential(2)}, ${ms.toFixed(2)} ms/step`);
process.exit(worst < 1e-4 ? 0 : 1);
