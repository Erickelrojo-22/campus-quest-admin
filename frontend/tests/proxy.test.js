import test from 'node:test';
import assert from 'node:assert/strict';
import { createProxy } from '../api/proxy.js';
function response() { return {headers:{},statusCode:200,setHeader(n,v){this.headers[n]=v;return this;},status(s){this.statusCode=s;return this;},json(b){this.body=b;return this;},send(b){this.body=b;return this;},end(){return this;}}; }
function request(extra={}) { return {method:'GET',url:'/api/proxy?path=misiones&incluirArchivadas=true',query:{path:'misiones'},headers:{},...extra}; }

test('proxy reenvía ruta, query, cookie y Origin al backend fijo',async () => {
  let call; const handler=createProxy(async (url,options) => {call={url,options};return Response.json([]);},() => 'https://backend.example.com');
  const res=response(); await handler(request({headers:{cookie:'campusquest_session=secret',origin:'https://frontend.example.com',host:'evil.test','x-forwarded-host':'evil.test'}}),res);
  assert.equal(call.url.href,'https://backend.example.com/api/v1/misiones?incluirArchivadas=true');
  assert.equal(call.options.headers.cookie,'campusquest_session=secret');
  assert.equal(call.options.headers.origin,'https://frontend.example.com');
  assert.equal(call.options.headers.host,undefined);
  assert.equal(call.options.headers['x-forwarded-host'],undefined);
  assert.equal(res.headers['Cache-Control'],'no-store');
});

test('login por proxy conserva JSON y cookie HttpOnly Secure',async () => {
  let body; const handler=createProxy(async (_,options) => {body=options.body;return new Response('{}',{status:200,headers:{'Set-Cookie':'campusquest_session=secret; Path=/; HttpOnly; Secure; SameSite=Lax'}});},() => 'https://backend.example.com');
  const res=response(); await handler(request({method:'POST',query:{path:'auth/login'},body:{correo:'admin@example.com',contrasena:'secret'}}),res);
  assert.deepEqual(JSON.parse(body),{correo:'admin@example.com',contrasena:'secret'});
  assert.match(res.headers['Set-Cookie'][0],/HttpOnly; Secure/);
});

test('logout conserva 204 y elimina la cookie en el origen frontend',async () => {
  const handler=createProxy(async () => new Response(null,{status:204,headers:{'Set-Cookie':'campusquest_session=""; Max-Age=0; Path=/'}}),() => 'https://backend.example.com');
  const res=response(); await handler(request({method:'POST',query:{path:'auth/logout'}}),res);
  assert.equal(res.statusCode,204); assert.match(res.headers['Set-Cookie'][0],/Max-Age=0/);
});

test('proxy impide cambiar el origen o escapar de /api/v1',async () => {
  const handler=createProxy(() => {throw new Error('No debe llamar fetch');},() => 'https://backend.example.com');
  for (const path of ['../../secret','https://evil.example.com','misiones%2F..']) { const res=response();await handler(request({query:{path}}),res);assert.equal(res.statusCode,404); }
});

test('configuración inválida y backend caído devuelven JSON',async () => {
  const missing=response();await createProxy(fetch,() => undefined)(request(),missing);assert.equal(missing.statusCode,503);
  let calls=0;
  const offline=response();await createProxy(async () => {calls++;throw new Error('Offline');},() => 'https://backend.example.com')(request({method:'POST',body:{titulo:'Nueva misión'}}),offline);assert.equal(offline.statusCode,502);assert.ok(offline.body.detail);
  assert.equal(calls,1,'Una mutación fallida no debe reenviarse automáticamente.');
  assert.doesNotMatch(offline.body.detail,/Railway/);
});

test('proxy rechaza paths duplicados y JSON inválido antes de llamar al backend',async () => {
  let calls=0;const handler=createProxy(async () => {calls++;return Response.json({});},() => 'https://backend.example.com');
  const duplicate=response();await handler(request({query:{path:['auth','login']}}),duplicate);assert.equal(duplicate.statusCode,404);
  const invalid=request({method:'POST'});Object.defineProperty(invalid,'body',{get(){throw new SyntaxError('Bad JSON');}});
  const bad=response();await handler(invalid,bad);assert.equal(bad.statusCode,400);assert.equal(calls,0);
});
