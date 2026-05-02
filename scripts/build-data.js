#!/usr/bin/env node
// Converts data/data.json → js/data.js so the app works without a server.
// Run: node scripts/build-data.js
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const json = JSON.parse(fs.readFileSync(path.join(root, 'data', 'data.json'), 'utf8'));
const output = `const APP_DATA = ${JSON.stringify(json, null, 2)};\n`;
fs.writeFileSync(path.join(root, 'js', 'data.js'), output);
console.log('js/data.js written successfully.');
