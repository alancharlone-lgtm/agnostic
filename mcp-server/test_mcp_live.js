import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";


// The Node TS sdk requires this if fetch is not global in older nodes, but node 18+ has it.

async function testMcp() {
    const transport = new SSEClientTransport(new URL("https://agnostic-mcp-server-532234202617.us-central1.run.app/sse"));
    const client = new Client({ name: "test-client", version: "1.0.0" }, { capabilities: {} });

    console.log("Conectando al servidor MCP...");
    await client.connect(transport);

    console.log("\n--- PRUEBA 1: buscar_tiendas_maps (Radio expansivo) ---");
    const result1 = await client.callTool({
        name: "buscar_tiendas_maps",
        arguments: {
            repuesto: "placa electronica lavavajillas",
            latitud: -34.6037,
            longitud: -58.3816,
            radio_km: 7
        }
    });
    console.log(JSON.parse(result1.content[0].text));

    console.log("\n--- PRUEBA 2: buscar_en_mercadolibre ---");
    const result2 = await client.callTool({
        name: "buscar_en_mercadolibre",
        arguments: {
            repuesto: "placa electronica drean concept 5.05"
        }
    });
    console.log(JSON.parse(result2.content[0].text));

    process.exit(0);
}

testMcp().catch(console.error);
