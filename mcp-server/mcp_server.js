import "dotenv/config";
import express from "express";
import cors from "cors";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import { z } from "zod";

const app = express();
app.use(cors());
app.use(express.json());

const PORT = process.env.PORT || 8080;
const MAPS_API_KEY = process.env.GOOGLE_MAPS_API_KEY;

// ─── MCP Server Factory ──────────────────────────────────────────────────────
function createMcpServer() {
  const mcpServer = new McpServer({
    name: "agnostic-mcp-server",
    version: "1.0.0",
  });

  // TOOL 1: consultar_inventario
  mcpServer.tool(
    "consultar_inventario",
    "Consulta si un repuesto está disponible en el inventario de la empresa.",
    {
      repuesto: z.string().describe("Nombre o código del repuesto a consultar"),
      id_tecnico: z.string().describe("ID único del técnico que realiza la consulta"),
    },
    async ({ repuesto, id_tecnico }) => {
      console.log(`[consultar_inventario] repuesto="${repuesto}", tecnico="${id_tecnico}"`);
      const inventarioMock = {
        "capacitor 45uf": { estado: "DISPONIBLE", cantidad: 12, ubicacion: "Depósito Central - Estante B3" },
        "termostato whirlpool": { estado: "DISPONIBLE", cantidad: 3, ubicacion: "Depósito Central - Estante A1" },
        "placa electronica samsung": { estado: "NO DISPONIBLE", cantidad: 0, ubicacion: null },
        "compresor lg": { estado: "DISPONIBLE", cantidad: 1, ubicacion: "Depósito Norte - Estante C7" },
      };
      const clave = repuesto.toLowerCase();
      const resultado = inventarioMock[clave] ?? { estado: "NO DISPONIBLE", cantidad: 0, ubicacion: null };
      return {
        content: [{ type: "text", text: JSON.stringify({ repuesto, id_tecnico, ...resultado }) }],
      };
    }
  );

  // TOOL 2: buscar_tiendas_maps
  mcpServer.tool(
    "buscar_tiendas_maps",
    "Busca tiendas de repuestos cercanas a la ubicación del técnico usando Google Maps.",
    {
      repuesto: z.string(),
      latitud: z.number(),
      longitud: z.number(),
      radio_km: z.number().optional(),
    },
    async ({ repuesto, latitud, longitud, radio_km }) => {
      const radio = Math.min(radio_km ?? 3, 50); // CAP AT 50KM TO AVOID ERROR 400
      console.log(`[buscar_tiendas_maps] repuesto="${repuesto}", radio=${radio}km`);
      const query = `tienda de repuestos ${repuesto} electrodomésticos`;
      const requestBody = {
        textQuery: query,
        locationBias: { circle: { center: { latitude: latitud, longitude: longitud }, radius: radio * 1000 } },
        maxResultCount: 10,
        languageCode: "es",
      };
      try {
        const response = await fetch("https://places.googleapis.com/v1/places:searchText", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Goog-Api-Key": MAPS_API_KEY, "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.websiteUri" },
          body: JSON.stringify(requestBody),
        });
        const data = await response.json();
        const places = data.places ?? [];
        const tiendas = places.map(p => ({
          nombre: p.displayName?.text, direccion: p.formattedAddress,
          website: p.websiteUri, tiene_web: !!p.websiteUri,
          coordenadas: { lat: p.location?.latitude, lng: p.location?.longitude }
        }));
        const conWeb = tiendas.filter(t => t.tiene_web);
        return {
          content: [{ type: "text", text: JSON.stringify({ repuesto, radio_km: radio, con_web: conWeb.length, tiendas }) }],
        };
      } catch (error) {
        return { content: [{ type: "text", text: JSON.stringify({ error: true, mensaje: error.message }) }], isError: true };
      }
    }
  );

  // TOOL 3: buscar_precios_web (SIN TOKEN - búsqueda web normal)
  mcpServer.tool(
    "buscar_en_mercadolibre",
    "Genera URLs de búsqueda para encontrar precios del repuesto en Argentina. El agente visita esas URLs para extraer precios reales.",
    { repuesto: z.string() },
    async ({ repuesto }) => {
      const qGoogle = encodeURIComponent(repuesto + " precio ARS argentina");
      const qML = encodeURIComponent(repuesto).replace(/%20/g, '-');
      const urls = [
        `https://www.google.com/search?q=${qGoogle}&gl=ar&hl=es`,
        `https://listado.mercadolibre.com.ar/${qML}`,
      ];
      console.log(`[buscar_precios_web] URLs generadas para: ${repuesto}`);
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            repuesto,
            instruccion: "Visitá cada URL para extraer precios reales en ARS y los nombres de las tiendas.",
            urls_a_visitar: urls
          })
        }]
      };
    }
  );


  // TOOL 4: calcular_tiempo_ruta
  mcpServer.tool(
    "calcular_tiempo_ruta",
    "Calcula el tiempo estimado de viaje en auto entre la ubicación del técnico y una tienda, usando Google Maps Distance Matrix API.",
    {
      origen_lat: z.number().describe("Latitud de origen (técnico)"),
      origen_lng: z.number().describe("Longitud de origen (técnico)"),
      destino_lat: z.number().describe("Latitud del destino (tienda)"),
      destino_lng: z.number().describe("Longitud del destino (tienda)"),
      nombre_tienda: z.string().optional().describe("Nombre de la tienda destino (solo para describir el resultado)"),
    },
    async ({ origen_lat, origen_lng, destino_lat, destino_lng, nombre_tienda }) => {
      const tienda = nombre_tienda ?? "destino";
      console.log(`[calcular_tiempo_ruta] De (${origen_lat},${origen_lng}) a ${tienda}`);
      const url = `https://maps.googleapis.com/maps/api/distancematrix/json?origins=${origen_lat},${origen_lng}&destinations=${destino_lat},${destino_lng}&mode=driving&language=es&key=${MAPS_API_KEY}`;
      try {
        const response = await fetch(url);
        const data = await response.json();
        const element = data?.rows?.[0]?.elements?.[0];
        if (!element || element.status !== "OK") {
          return {
            content: [{ type: "text", text: JSON.stringify({ error: true, mensaje: `No se pudo calcular la ruta a ${tienda}. Status: ${element?.status}` }) }],
            isError: true,
          };
        }
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              tienda,
              distancia_texto: element.distance.text,
              distancia_metros: element.distance.value,
              duracion_texto: element.duration.text,
              duracion_segundos: element.duration.value,
            })
          }],
        };
      } catch (error) {
        return { content: [{ type: "text", text: JSON.stringify({ error: true, mensaje: error.message }) }], isError: true };
      }
    }
  );

  // TOOL 5: generar_guia_visual_nanobanana
  mcpServer.tool(
    "generar_guia_visual_nanobanana",
    "Usa la API de Nano Banana 2 (Gemini 3.1 Flash Image Preview) para editar una imagen técnica con guías visuales.",
    {
      image_base64: z.string().describe("La imagen original en base64 capturada por la cámara."),
      prompt_tecnico: z.string().describe("Instrucciones precisas sobre qué dibujar, resaltar o señalar en la imagen técnica."),
    },
    async ({ image_base64, prompt_tecnico }) => {
      console.log(`[generar_guia_visual_nanobanana] Procesando imagen con prompt técnico.`);
      const API_KEY = process.env.GOOGLE_GENAI_API_KEY || process.env.GEMINI_API_KEY;

      if (!API_KEY) {
        return {
          content: [{ type: "text", text: JSON.stringify({ error: true, mensaje: "API Key de Gemini no configurada en el servidor MCP." }) }],
          isError: true,
        };
      }

      const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent?key=${API_KEY}`;

      const clean_base64 = image_base64.replace(/^data:image\/\w+;base64,/, "").trim();

      const requestBody = {
        contents: [{
          parts: [
            { text: prompt_tecnico },
            { inline_data: { mime_type: "image/jpeg", data: clean_base64 } }
          ]
        }],
        safetySettings: [
          { category: "HARM_CATEGORY_HATE_SPEECH", threshold: "BLOCK_NONE" },
          { category: "HARM_CATEGORY_HARASSMENT", threshold: "BLOCK_NONE" },
          { category: "HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold: "BLOCK_NONE" },
          { category: "HARM_CATEGORY_DANGEROUS_CONTENT", threshold: "BLOCK_NONE" }
        ]
      };

      try {
        const response = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
          const errText = await response.text();
          throw new Error(`Gemini API error ${response.status}: ${errText}`);
        }

        const data = await response.json();
        const candidate = data.candidates?.[0];
        let resultImageBase64 = null;

        if (candidate?.content?.parts) {
          for (const part of candidate.content.parts) {
            if (part.inlineData?.data) {
              resultImageBase64 = part.inlineData.data;
              break;
            }
          }
        }

        if (resultImageBase64) {
          return {
            content: [{
              type: "text",
              text: JSON.stringify({
                status: "success",
                message: "Imagen editada exitosamente.",
                image_base64: resultImageBase64
              })
            }]
          };
        } else {
          return {
            content: [{
              type: "text",
              text: JSON.stringify({
                error: true,
                mensaje: "El modelo no devolvió una imagen editada. Verifique el prompt o la imagen de entrada.",
                raw_response: JSON.stringify(data).substring(0, 500)
              })
            }],
            isError: true
          };
        }
      } catch (error) {
        console.error(`[generar_guia_visual_nanobanana] Error:`, error);
        return { content: [{ type: "text", text: JSON.stringify({ error: true, mensaje: error.message }) }], isError: true };
      }
    }
  );

  return mcpServer;
}

// ─── Express Endpoints (SSE Transport) ───────────────────────────────────────
const activeTransports = {};

app.get("/sse", async (req, res) => {
  console.log("[SSE] New client connected");
  const transport = new SSEServerTransport("/messages", res);
  activeTransports[transport.sessionId] = transport;

  res.on("close", () => {
    console.log(`[SSE] Client ${transport.sessionId} disconnected`);
    delete activeTransports[transport.sessionId];
  });

  try {
    const serverInstance = createMcpServer();
    await serverInstance.connect(transport);
  } catch (err) {
    console.error(`[SSE] Critical Error:`, err);
    if (!res.headersSent) res.status(500).json({ error: err.message });
  }
});

app.post("/messages", async (req, res) => {
  const sessionId = req.query.sessionId;
  const transport = activeTransports[sessionId];

  if (!transport) {
    console.warn(`[Messages] Session ${sessionId} not found`);
    return res.status(404).json({ error: "Session not found" });
  }

  console.log(`[Messages] Incoming raw body length from python:`, JSON.stringify(req.body).length);
  console.log(`[Messages] Payload snippet:`, JSON.stringify(req.body).substring(0, 300));

  // express.json() ya consumió el stream del body y lo parseó en req.body.
  // Pasamos req.body como 3er parámetro para evitar que el SDK intente leer el body de nuevo.
  await transport.handlePostMessage(req, res, req.body);
});

// Health check para Cloud Run
app.get("/health", (req, res) => {
  res.json({ status: "ok", server: "agnostic-mcp-server", version: "1.0.0" });
});

app.listen(PORT, () => {
  console.log(`🚀 Agnostic MCP Server running on port ${PORT}`);
  console.log(`   SSE endpoint:     GET  /sse`);
  console.log(`   Messages endpoint: POST /messages`);
  console.log(`   Health check:      GET  /health`);
  if (!MAPS_API_KEY) {
    console.warn("⚠️  GOOGLE_MAPS_API_KEY not set in environment variables!");
  }
});
