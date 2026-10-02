// Catálogo original de Gamequest/data/local/SeedData.kt. Usuarios y progreso se simulan por separado.
export const puntosIniciales = [
  {
    "id": 1,
    "nombre": "Biblioteca central",
    "categoria": "Académico",
    "descripcion": "Sala de lectura, préstamo de libros y salas de estudio grupal.",
    "horarioAtencion": "Lunes a viernes, 07:30 a 19:00",
    "tramites": "Préstamo y devolución de libros, carné de biblioteca, salas de estudio",
    "codigoQr": "CQ-BIB-001",
    "posX": 0.22,
    "posY": 0.3
  },
  {
    "id": 2,
    "nombre": "Secretaría académica",
    "categoria": "Trámites",
    "descripcion": "Edificio administrativo. Recepción de documentos de matrícula, certificados y constancias.",
    "horarioAtencion": "Lunes a viernes, 08:00 a 16:30",
    "tramites": "Entrega de documentos de matrícula, constancias, cambios de datos",
    "codigoQr": "CQ-SEC-002",
    "posX": 0.62,
    "posY": 0.22
  },
  {
    "id": 3,
    "nombre": "Laboratorio de software",
    "categoria": "Académico",
    "descripcion": "Bloque C, aula 204. Equipos para prácticas de programación y desarrollo móvil.",
    "horarioAtencion": "Lunes a sábado, 07:00 a 21:00",
    "tramites": "Reserva de equipos, soporte técnico de laboratorio",
    "codigoQr": "CQ-LAB-003",
    "posX": 0.2,
    "posY": 0.68
  },
  {
    "id": 4,
    "nombre": "Bienestar estudiantil",
    "categoria": "Servicios",
    "descripcion": "Orientación psicológica, becas y acompañamiento a estudiantes nuevos.",
    "horarioAtencion": "Lunes a viernes, 08:00 a 17:00",
    "tramites": "Solicitud de becas, orientación psicológica, tutorías",
    "codigoQr": "CQ-BIE-004",
    "posX": 0.78,
    "posY": 0.55
  },
  {
    "id": 5,
    "nombre": "Cafetería central",
    "categoria": "Servicios",
    "descripcion": "Zona de comida y descanso entre clases.",
    "horarioAtencion": "Lunes a viernes, 07:00 a 18:00",
    "tramites": "Venta de alimentos, punto de encuentro",
    "codigoQr": "CQ-CAF-005",
    "posX": 0.45,
    "posY": 0.8
  },
  {
    "id": 6,
    "nombre": "Canchas deportivas",
    "categoria": "Recreación",
    "descripcion": "Espacios para fútbol, básquet y actividades del área de cultura física.",
    "horarioAtencion": "Lunes a sábado, 07:00 a 20:00",
    "tramites": "Reserva de canchas, inscripción a torneos internos",
    "codigoQr": "CQ-CAN-006",
    "posX": 0.85,
    "posY": 0.82
  },
  {
    "id": 7,
    "nombre": "Ventanilla de certificados",
    "categoria": "Trámites",
    "descripcion": "Emisión de certificados de matrícula, notas y egresamiento.",
    "horarioAtencion": "Lunes a viernes, 08:00 a 12:30 y 14:00 a 16:30",
    "tramites": "Certificado de matrícula (cédula y número de matrícula), certificado de notas",
    "codigoQr": "CQ-CER-007",
    "posX": 0.6,
    "posY": 0.4
  },
  {
    "id": 8,
    "nombre": "Centro de cómputo",
    "categoria": "Académico",
    "descripcion": "Sala de computadoras de uso libre para trabajos e investigación.",
    "horarioAtencion": "Lunes a viernes, 08:00 a 20:00",
    "tramites": "Uso libre de equipos, impresión de documentos",
    "codigoQr": "CQ-COM-008",
    "posX": 0.35,
    "posY": 0.5
  }
];

export const misionesIniciales = [
  {
    "id": 1,
    "puntoInteresId": 1,
    "activa": true,
    "titulo": "Encuentra la biblioteca",
    "descripcionPista": "Bloque B, planta baja. Llega al mostrador de atención y escanea el código QR para validar tu visita.",
    "insigniaNombre": "Ratón de biblioteca",
    "insigniaEmoji": "📚",
    "puntos": 50,
    "tiempoEstimadoMin": 15,
    "dificultad": "Media"
  },
  {
    "id": 2,
    "puntoInteresId": 2,
    "activa": true,
    "titulo": "Ubica secretaría académica",
    "descripcionPista": "Edificio administrativo, primera planta, ventanilla 2. Escanea el código QR de la ventanilla.",
    "insigniaNombre": "Trámites resueltos",
    "insigniaEmoji": "🏛️",
    "puntos": 30,
    "tiempoEstimadoMin": 10,
    "dificultad": "Baja"
  },
  {
    "id": 3,
    "puntoInteresId": 3,
    "activa": true,
    "titulo": "Visita el laboratorio de software",
    "descripcionPista": "Bloque C, aula 204. Sube al segundo piso y busca la puerta con el mural de código.",
    "insigniaNombre": "Futuro ingeniero",
    "insigniaEmoji": "💻",
    "puntos": 80,
    "tiempoEstimadoMin": 20,
    "dificultad": "Alta"
  },
  {
    "id": 4,
    "puntoInteresId": 4,
    "activa": true,
    "titulo": "Conoce bienestar estudiantil",
    "descripcionPista": "Junto al bloque administrativo. Pregunta por la oferta de becas para nuevo ingreso.",
    "insigniaNombre": "Bien acompañado",
    "insigniaEmoji": "💚",
    "puntos": 40,
    "tiempoEstimadoMin": 12,
    "dificultad": "Media"
  },
  {
    "id": 5,
    "puntoInteresId": 5,
    "activa": true,
    "titulo": "Descubre la cafetería central",
    "descripcionPista": "En el patio central. Ideal para tu primer descanso entre clases.",
    "insigniaNombre": "Buen provecho",
    "insigniaEmoji": "☕",
    "puntos": 20,
    "tiempoEstimadoMin": 8,
    "dificultad": "Baja"
  },
  {
    "id": 6,
    "puntoInteresId": 6,
    "activa": true,
    "titulo": "Explora las canchas deportivas",
    "descripcionPista": "Al fondo del campus. Sigue el camino después de la cafetería.",
    "insigniaNombre": "Espíritu deportivo",
    "insigniaEmoji": "⚽",
    "puntos": 30,
    "tiempoEstimadoMin": 10,
    "dificultad": "Baja"
  },
  {
    "id": 7,
    "puntoInteresId": 7,
    "activa": true,
    "titulo": "Solicita un certificado",
    "descripcionPista": "Junto a secretaría académica. Lleva tu cédula y número de matrícula.",
    "insigniaNombre": "Gestor eficiente",
    "insigniaEmoji": "📄",
    "puntos": 35,
    "tiempoEstimadoMin": 10,
    "dificultad": "Media"
  },
  {
    "id": 8,
    "puntoInteresId": 8,
    "activa": true,
    "titulo": "Conoce el centro de cómputo",
    "descripcionPista": "Cerca del laboratorio de software. Pregunta por el horario de uso libre.",
    "insigniaNombre": "Conectado",
    "insigniaEmoji": "🖥️",
    "puntos": 40,
    "tiempoEstimadoMin": 10,
    "dificultad": "Media"
  }
];
