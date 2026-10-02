/** Vercel-only proxy: keep the browser cookie on the frontend's HTTPS origin. */
export function createProxy(fetcher=globalThis.fetch,getBackendUrl=() => process.env.BACKEND_URL) {
  return async function handler(req,res) {
    res.setHeader('Cache-Control','no-store');
    const fail=(status,detail) => res.status(status).json({detail});
    const methods=['GET','HEAD','POST','PUT','DELETE','OPTIONS'];
    if (!methods.includes(req.method)) return fail(405,'Método no permitido.');
    let origin;
    try {
      origin=new URL(getBackendUrl());
      if (origin.protocol!=='https:' || origin.pathname!=='/' || origin.search || origin.hash || origin.username || origin.password) throw new Error();
    } catch { return fail(503,'Configura BACKEND_URL en Vercel con el origen HTTPS del backend.'); }
    const incoming=new URL(req.url,'https://proxy.invalid');
    const raw=req.query?.path ?? incoming.searchParams.get('path') ?? '';
    if (typeof raw!=='string') return fail(404,'Ruta API no encontrada.');
    const path=raw;
    if (!path || !/^[a-zA-Z0-9_-]+(?:\/[a-zA-Z0-9_-]+)*\/?$/.test(path)) return fail(404,'Ruta API no encontrada.');
    const target=new URL(`/api/v1/${path}`,origin);
    incoming.searchParams.delete('path');
    target.search=incoming.searchParams.toString();
    const headers={Accept:'application/json'};
    // Never forward Host, X-Forwarded-* or arbitrary user-supplied proxy headers.
    for (const name of ['authorization','cookie','origin','content-type']) {
      const value=req.headers[name];
      if (value) headers[name]=Array.isArray(value) ? value.join(', ') : value;
    }
    // Give a sleeping free-tier backend time to start; send each request once.
    const options={method:req.method,headers,redirect:'manual',signal:AbortSignal.timeout(90000)};
    try {
      if (!['GET','HEAD'].includes(req.method) && req.body!==undefined && req.body!==null) {
        if (headers['content-type'] && !headers['content-type'].toLowerCase().startsWith('application/json')) return fail(415,'Esta API solo acepta cuerpos JSON.');
        headers['content-type']='application/json';
        options.body=typeof req.body==='string' || Buffer.isBuffer(req.body) ? req.body : JSON.stringify(req.body);
      }
    } catch { return fail(400,'El cuerpo de la petición no es JSON válido.'); }
    try {
      const upstream=await fetcher(target,options);
      const cookies=upstream.headers.getSetCookie();
      if (cookies.length) res.setHeader('Set-Cookie',cookies);
      const type=upstream.headers.get('content-type');
      if (type) res.setHeader('Content-Type',type);
      const location=upstream.headers.get('location');
      if (location) {
        const redirect=new URL(location,target);
        if (redirect.origin!==origin.origin || !redirect.pathname.startsWith('/api/v1/')) return fail(502,'El backend devolvió una redirección no válida.');
        res.setHeader('Location',redirect.pathname+redirect.search);
      }
      res.status(upstream.status);
      if (req.method==='HEAD' || upstream.status===204) return res.end();
      return res.send(Buffer.from(await upstream.arrayBuffer()));
    } catch { return fail(502,'No se pudo contactar con el backend. Revisa BACKEND_URL y el estado del servicio.'); }
  };
}
export default createProxy();
