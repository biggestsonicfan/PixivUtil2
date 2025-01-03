const puppeteer = require('puppeteer');

(async () => {
    try {
        // Read HTML from stdin
        let inputData = '';
        process.stdin.on('data', chunk => {
            inputData += chunk;
        });

        process.stdin.on('end', async () => {
            const data = JSON.parse(inputData);
            const { headers, html } = data;
            // Launch Puppeteer
            const browser = await puppeteer.launch();
            const page = await browser.newPage();

            // Set headers on the page
            await page.setExtraHTTPHeaders(headers);

            // Load the HTML content
            await page.setContent(html);

            // Get the rendered content
            const renderedContent = await page.content();

            console.log(renderedContent);

            await browser.close();
        });
    } catch (error) {
        console.error('Error rendering page:', error);
        process.exit(1);
    }
})();
