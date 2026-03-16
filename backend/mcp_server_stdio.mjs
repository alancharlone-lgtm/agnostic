/**
 * mcp_server_stdio.js
 * Variante STDIO del servidor MCP de Agnostic.
 * Usado por el ADK de Google (StdioServerParameters) para evitar el bug de anyio/SSE.
 * Las herramientas son idénticas a mcp_server.js pero el transporte es stdin/stdout.
 */

import "dotenv/config";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const MAPS_API_KEY = process.env.GOOGLE_MAPS_API_KEY;

const mcpServer = new McpServer({
    name: "agnostic-mcp-server-stdio",
    version: "1.0.0",
});

// ─── TOOL 1: consultar_inventario (Mock camioneta del técnico) ─────────────────
mcpServer.tool(
    "consultar_inventario",
    "Consulta si un repuesto está disponible en el inventario de la camioneta del técnico.",
    {
        repuesto: z.string().describe("Nombre o código del repuesto a consultar"),
        id_tecnico: z.string().describe("ID único del técnico que realiza la consulta"),
    },
    async ({ repuesto, id_tecnico }) => {
        const inventarioMock = {
            "capacitor 45uf": { estado: "DISPONIBLE", cantidad: 12, ubicacion: "Camioneta - Caja B3" },
            "termostato whirlpool": { estado: "DISPONIBLE", cantidad: 3, ubicacion: "Camioneta - Caja A1" },
            "placa electronica samsung": { estado: "NO DISPONIBLE", cantidad: 0, ubicacion: null },
            "compresor lg": { estado: "DISPONIBLE", cantidad: 1, ubicacion: "Camioneta - Caja C7" },
        };

        const clave = repuesto.toLowerCase();
        const resultado = inventarioMock[clave] ?? { estado: "NO DISPONIBLE", cantidad: 0, ubicacion: null };

        return {
            content: [{
                type: "text",
                text: JSON.stringify({
                    repuesto, id_tecnico, ...resultado,
                    mensaje: resultado.estado === "DISPONIBLE"
                        ? `El repuesto "${repuesto}" está disponible en ${resultado.ubicacion}.`
                        : `El repuesto "${repuesto}" no está disponible en la camioneta.`,
                }),
            }],
        };
    }
);

// ─── TOOL 2: buscar_tiendas_maps (Google Places API v1 — radio expansivo + website) ──
mcpServer.tool(
    "buscar_tiendas_maps",
    "Busca tiendas de repuestos cercanas usando Google Maps. Devuelve nombre, dirección, teléfono, coordenadas y sitio web. Llamar con radio_km creciente (3 → 7 → 15) si no hay tiendas con web.",
    {
        repuesto: z.string(),
        latitud: z.number(),
        longitud: z.number(),
        radio_km: z.number().optional().describe("Radio en km. Default: 3. Usar 3, 7 o 15 progresivamente."),
    },
    async ({ repuesto, latitud, longitud, radio_km }) => {
        const radio = radio_km ?? 3;
        const query = `tienda de repuestos ${repuesto} electrodomésticos`;
        const requestBody = {
            textQuery: query,
            locationBias: {
                circle: {
                    center: { latitude: latitud, longitude: longitud },
                    radius: radio * 1000,
                },
            },
            maxResultCount: 5,
            languageCode: "es",
        };

        try {
            const response = await fetch("https://places.googleapis.com/v1/places:searchText", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": MAPS_API_KEY,
                    "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.rating,places.internationalPhoneNumber,places.websiteUri",
                },
                body: JSON.stringify(requestBody),
            });

            if (!response.ok) {
                const errText = await response.text();
                throw new Error(`Google Places API error ${response.status}: ${errText}`);
            }

            const data = await response.json();
            const places = data.places ?? [];
            const tiendas = places.map((place) => ({
                nombre: place.displayName?.text ?? "Sin nombre",
                direccion: place.formattedAddress ?? "Dirección no disponible",
                telefono: place.internationalPhoneNumber ?? null,
                website: place.websiteUri ?? null,
                tiene_web: !!place.websiteUri,
                rating: place.rating ?? null,
                coordenadas: { lat: place.location?.latitude ?? null, lng: place.location?.longitude ?? null },
            }));

            const conWeb = tiendas.filter(t => t.tiene_web);

            return {
                content: [{
                    type: "text",
                    text: JSON.stringify({
                        repuesto, radio_km: radio,
                        ubicacion_tecnico: { latitud, longitud },
                        total_encontradas: tiendas.length,
                        con_web: conWeb.length,
                        tiendas,
                        instruccion_agente: conWeb.length === 0
                            ? `Ninguna de las ${tiendas.length} tiendas en ${radio}km tiene web. Llamar con radio_km=${radio < 7 ? 7 : 15}.`
                            : `Se encontraron ${conWeb.length} tiendas con web. Verificar stock con url_context.`,
                    }),
                }],
            };
        } catch (error) {
            return {
                content: [{ type: "text", text: JSON.stringify({ error: true, mensaje: error.message }) }],
                isError: true,
            };
        }
    }
);

// ─── TOOL 3: buscar_en_mercadolibre (API pública MercadoLibre Argentina) ─────
mcpServer.tool(
    "buscar_en_mercadolibre",
    "Busca un repuesto en MercadoLibre Argentina y devuelve los 3 resultados más baratos con precio, título y link.",
    { repuesto: z.string() },
    async ({ repuesto }) => {
        try {
            const url = `https://api.mercadolibre.com/sites/MLA/search?q=${encodeURIComponent(repuesto)}&limit=5&sort=price_asc`;
            const response = await fetch(url, { headers: { "User-Agent": "AgnosticApp/1.0" } });

            if (!response.ok) throw new Error(`MercadoLibre API error ${response.status}`);

            const data = await response.json();
            const results = data.results ?? [];

            if (results.length === 0) {
                return { content: [{ type: "text", text: JSON.stringify({ repuesto, total: 0, mensaje: "No se encontraron resultados.", resultados: [] }) }] };
            }

            const top3 = results.slice(0, 3).map(item => ({
                titulo: item.title,
                precio_ars: item.price,
                moneda: item.currency_id,
                link: item.permalink,
                condicion: item.condition === "new" ? "Nuevo" : "Usado",
                vendedor: item.seller?.nickname ?? "Desconocido",
                envio_gratis: item.shipping?.free_shipping ?? false,
            }));

            const precios = top3.map(i => i.precio_ars);
            const promedio = Math.round(precios.reduce((a, b) => a + b, 0) / precios.length);
            const minimo = Math.min(...precios);

            return {
                content: [{
                    type: "text",
                    text: JSON.stringify({
                        repuesto, total_encontrados: results.length,
                        precio_minimo_ars: minimo, precio_promedio_ars: promedio,
                        top_3_resultados: top3,
                        mensaje: `Precio de referencia: desde $${minimo.toLocaleString('es-AR')} ARS. Promedio top 3: $${promedio.toLocaleString('es-AR')} ARS.`,
                    }),
                }],
            };
        } catch (error) {
            return { content: [{ type: "text", text: JSON.stringify({ error: true, mensaje: error.message }) }], isError: true };
        }
    }
);

// ─── TOOL 4: calcular_tiempo_ruta (Google Routes API v2) ─────────────────────
mcpServer.tool(
    "calcular_tiempo_ruta",
    "Calcula el tiempo y distancia de ruta entre dos puntos usando Google Maps con tráfico en tiempo real.",
    {
        origen_lat: z.number(),
        origen_lng: z.number(),
        destino_lat: z.number(),
        destino_lng: z.number(),
    },
    async ({ origen_lat, origen_lng, destino_lat, destino_lng }) => {
        const requestBody = {
            origin: { location: { latLng: { latitude: origen_lat, longitude: origen_lng } } },
            destination: { location: { latLng: { latitude: destino_lat, longitude: destino_lng } } },
            travelMode: "DRIVE",
            routingPreference: "TRAFFIC_AWARE",
            computeAlternativeRoutes: false,
            languageCode: "es",
            units: "METRIC",
        };

        try {
            const response = await fetch("https://routes.googleapis.com/directions/v2:computeRoutes", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": MAPS_API_KEY,
                    "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.description",
                },
                body: JSON.stringify(requestBody),
            });

            if (!response.ok) {
                const errText = await response.text();
                throw new Error(`Google Routes API error ${response.status}: ${errText}`);
            }

            const data = await response.json();
            const route = data.routes?.[0];
            if (!route) throw new Error("No se encontró ninguna ruta válida.");

            const segundos = parseInt(route.duration?.replace("s", "") ?? "0", 10);
            const minutos = Math.ceil(segundos / 60);
            const distanciaKm = ((route.distanceMeters ?? 0) / 1000).toFixed(1);

            return {
                content: [{
                    type: "text",
                    text: JSON.stringify({
                        origen: { lat: origen_lat, lng: origen_lng },
                        destino: { lat: destino_lat, lng: destino_lng },
                        distancia_km: parseFloat(distanciaKm),
                        duracion_minutos: minutos,
                        duracion_texto: `${minutos} minutos`,
                        con_trafico: true,
                        mensaje: `La tienda está a ${distanciaKm} km. Tiempo estimado con tráfico: ${minutos} minutos.`,
                    }),
                }],
            };
        } catch (error) {
            return { content: [{ type: "text", text: JSON.stringify({ error: true, mensaje: error.message }) }], isError: true };
        }
    }
);

// ─── Arranque con transporte STDIO ───────────────────────────────────────────
const transport = new StdioServerTransport();
await mcpServer.connect(transport);
