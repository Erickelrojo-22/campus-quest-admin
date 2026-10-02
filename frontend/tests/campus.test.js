import test from 'node:test';
import assert from 'node:assert/strict';
import { createApiClient, createDemoClient, ApiError } from '../src/services/campus.js';
import { csvCell, filterPeriod } from '../src/services/utils.js';

test('el cliente API respeta cookies y el contrato camelCase al guardar',async () => {
  const calls=[]; const api=createApiClient('/api/v1/',async (url,options) => { calls.push({url,options}); return new Response(JSON.stringify({id:9}),{status:201}); });
  await api.saveMission({id:9,titulo:'Misión de prueba',puntos:30,activa:true});
  assert.equal(calls[0].url,'/api/v1/misiones/9');
  assert.equal(calls[0].options.method,'PUT');
  assert.equal(calls[0].options.credentials,'include');
  assert.deepEqual(JSON.parse(calls[0].options.body),{titulo:'Misión de prueba',puntos:30,activa:true});
});

test('un fallo de API nunca introduce datos de demostración',async () => {
  const api=createApiClient('/api/v1',async () => new Response(JSON.stringify({detail:'Sin sesión'}),{status:401}));
  await assert.rejects(api.load(),e => e instanceof ApiError && e.status===401 && e.message==='Sin sesión');
});

test('detecta una URL que devuelve HTML en lugar de JSON',async () => {
  const api=createApiClient('/wrong',async () => new Response('<html/>'));
  await assert.rejects(api.me(),/no devolvió JSON/);
});

test('interpreta errores de campos de FastAPI',async () => {
  const api=createApiClient('/api/v1',async () => new Response(JSON.stringify({detail:[{loc:['body','puntos'],msg:'Debe ser positivo'}]}),{status:422}));
  await assert.rejects(api.saveMission({titulo:'X'}),e => e.status===422 && e.message==='puntos: Debe ser positivo');
});

test('archivar una misión demo conserva puntos e historial; reset restaura catálogo',async () => {
  const demo=createDemoClient(); const before=await demo.load();
  await demo.archiveMission(1); const after=await demo.load();
  assert.equal(after.misiones.find(m => m.id===1).activa,false);
  assert.deepEqual(after.progreso,before.progreso);
  assert.deepEqual(after.usuarios,before.usuarios);
  await demo.reset(); assert.equal((await demo.load()).misiones.find(m => m.id===1).activa,true);
});

test('demo mantiene QR único y no cambia de lugar una misión con progreso',async () => {
  const demo=createDemoClient(); const data=await demo.load();
  await assert.rejects(demo.savePoint({...data.puntos[1],codigoQr:' cq-bib-001 '}),e => e.status===409);
  await assert.rejects(demo.saveMission({...data.misiones[0],puntoInteresId:2}),e => e.status===409);
});

test('los CSV neutralizan fórmulas y escapan comillas',() => {
  assert.equal(csvCell('=HYPERLINK("x")'),'"\'=HYPERLINK(""x"")"');
  assert.equal(csvCell('@SUM(1)'),'"\'@SUM(1)"');
  assert.equal(csvCell('Mateo, Rivera'),'"Mateo, Rivera"');
  assert.equal(csvCell(120),'"120"');
});

test('los periodos excluyen registros futuros y respetan el límite inicial',() => {
  const now=20*86400000; const data=[{fechaHora:now-7*86400000},{fechaHora:now-8*86400000},{fechaHora:now+1}];
  assert.equal(filterPeriod(data,7,now).length,1);
  assert.equal(filterPeriod(data,0,now).length,2);
});
