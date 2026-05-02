#!/usr/bin/env node
// Converts src/data/data.json → src/js/data.js so the app works without a server.
// Run: node scripts/build-data.js
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const json = JSON.parse(fs.readFileSync(path.join(root, 'src', 'data', 'data.json'), 'utf8'));
const output = `const APP_DATA = ${JSON.stringify(json, null, 2)};\n`;
fs.writeFileSync(path.join(root, 'src', 'js', 'data.js'), output);
console.log('src/js/data.js written successfully.');
