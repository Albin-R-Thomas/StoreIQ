// Contract-shaped stand-in, never a substitute for a live model quality evaluation.
const http = require('http');
http.createServer(async (req, res) => {
  let raw = '';
  for await (const chunk of req) raw += chunk;
  let body = req.body;
  try { if (!body || typeof body !== 'object') body = JSON.parse(raw || '{}'); }
  catch { res.writeHead(400, {'Content-Type':'application/json'}); return res.end(JSON.stringify({error:{message:'Invalid JSON',type:'invalid_request_error'}})); }
  const send = (status, value) => {res.writeHead(status, {'Content-Type':'application/json'});res.end(JSON.stringify(value));};
  if (JSON.stringify(body).includes('SIMULATE_FAILURE')) return send(503,{error:{message:'Injected provider outage',type:'server_error'}});
  if(req.url === '/v1/embeddings') {
    const inputs = Array.isArray(body.input) ? body.input : [body.input];
    return send(200,{object:'list',model:body.model,data:inputs.map((_,index)=>({object:'embedding',index,embedding:[0.2,0.4,0.1,0.8]})),usage:{prompt_tokens:10,total_tokens:10}});
  }
  if(req.url !== '/v1/responses') return send(501,{error:{message:'Endpoint not modelled',type:'invalid_request_error'}});
  const schema = body.text?.format?.name;
  let value;
  if(schema === 'ExtractedHome') value = {distance:null,light:null,use:null,seating:null,problem:null,placement:null,budget:null};
  else if(schema === 'OptimizedQuery') value = {query:'Samsung Vision Q55 native refresh rate 120 Hz cricket motion',relevant:true};
  else if(schema === 'Answer') value = {lines:['Samsung Vision Q55 has a native 120 Hz refresh rate in the synthetic catalogue.','Compare the same cricket clip at matched settings for this home.'],source_ids:['samsung-q55'],unsupported:false};
  else return send(400,{error:{message:'Unknown structured schema',type:'invalid_request_error'}});
  send(200,{id:'resp_fixture',object:'response',created_at:1793491200,status:'completed',model:body.model,
    output:[{type:'message',id:'msg_fixture',status:'completed',role:'assistant',content:[{type:'output_text',text:JSON.stringify(value),annotations:[]}]}],
    usage:{input_tokens:30,output_tokens:30,total_tokens:60}});
}).listen(process.env.PORT || 4011);
