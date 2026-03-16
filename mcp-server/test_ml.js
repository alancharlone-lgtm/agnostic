// Using global fetch (available in Node 18+)

async function testML() {
    const repuesto = "bomba de desagote universal lavarropas";
    const url = `https://api.mercadolibre.com/sites/MLA/search?q=${encodeURIComponent(repuesto)}&limit=5&sort=price_asc`;
    try {
        console.log(`Testing URL: ${url}`);
        const response = await fetch(url);
        console.log(`Status: ${response.status}`);
        const data = await response.json();
        console.log(`Results count: ${data.results?.length || 0}`);
        if (data.results && data.results.length > 0) {
            console.log("Top result:", data.results[0].title, data.results[0].price);
        } else {
            console.log("No results found. Full data snippet:", JSON.stringify(data).substring(0, 500));
        }
    } catch (e) {
        console.error("Error:", e.message);
    }
}

testML();
