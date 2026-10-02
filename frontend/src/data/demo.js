import { misionesIniciales, puntosIniciales } from './catalog.js';

// Personas ficticias; el catálogo sí procede de SeedData.kt de Android.
export function createDemoData() {
  const nombres = ['Sofía Mendoza', 'Mateo Rivera', 'Valentina Castro', 'Sebastián Torres', 'Camila López', 'Daniel Vera', 'Isabella Ruiz', 'Nicolás Bravo', 'Lucía Moreira', 'Andrés Zambrano', 'Ana García', 'Gabriel León'];
  const carreras = ['Ingeniería de Software', 'Administración', 'Comunicación', 'Arquitectura'];
  const completadas = [[1,2,3,4,5,6,7,8], [1,2,3,5,8], [1,2,4,5], [1,3,8], [1,2,5,6], [2,5,7], [1,4], [2,6], [5], [1,2], [], []];
  const progreso = [];
  const ahora = new Date(); ahora.setHours(12,0,0,0);
  const usuarios = nombres.map((nombres,i) => {
    completadas[i].forEach((misionId,j) => {
      const mision = misionesIniciales.find(m => m.id === misionId);
      const punto = puntosIniciales.find(p => p.id === mision.puntoInteresId);
      progreso.push({ id:progreso.length+1, usuarioId:i+1, misionId, fechaHora:ahora.getTime()-((i+j)%7)*86400000+(j*15-i*10)*60000, puntosObtenidos:mision.puntos, codigoQrValidado:punto.codigoQr, estado:'completada' });
    });
    const puntajeAcumulado = progreso.filter(p => p.usuarioId === i+1).reduce((s,p) => s+p.puntosObtenidos,0);
    return { id:i+1, nombres, correoInstitucional:i>=10 ? '' : `estudiante${i+1}@example.com`, carrera:i>=10 ? 'Visita al campus' : carreras[i%4], puntajeAcumulado, nivel:1+Math.floor(puntajeAcumulado/100), rol:i>=10 ? 'visitante' : 'estudiante' };
  });
  return { usuarios, misiones:structuredClone(misionesIniciales), puntos:structuredClone(puntosIniciales), progreso };
}
