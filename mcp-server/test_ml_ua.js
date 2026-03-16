// Using global fetch (available in Node 18+)
async function testML_UA() {
    const repuesto = "bomba de desagote universal lavarropas";
    const url = `https://api.mercadolibre.com/sites/MLA/search?q=${encodeURIComponent(repuesto)}&limit=5&sort=price_asc`;
    try {
        console.log(`Testing URL with User-Agent: ${url}`);
        const response = await fetch(url, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json'
            }
        });
        console.log(`Status: ${response.status}`);
        const data = await response.json();
        if (response.status === 200) {
            console.log(`Results count: ${data.results?.length || 0}`);
            if (data.results && data.results.length > 0) {
                console.log("Top result:", data.results[0].title, data.results[0].price);
            }
        } else {
            console.log("Failed. Status:", response.status, "Message:", data.message);
        }
    } catch (e) {
        console.error("Error:", e.message);
    }
}

testML_UA();
