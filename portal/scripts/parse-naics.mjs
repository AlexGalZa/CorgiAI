// Quick script to parse NAICS CSV into a compact JSON for the autocomplete
import { readFileSync, writeFileSync } from 'fs';

const csv = readFileSync('C:\\Users\\sergi\\Downloads\\2022_titles_descriptions.csv', 'utf-8');
const lines = csv.split('\n');
const entries = [];

for (let i = 1; i < lines.length; i++) {
  const line = lines[i].trim();
  if (!line) continue;
  
  // Parse CSV with quoted fields
  const match = line.match(/^"([^"]+)","([^"]+)"/);
  if (!match) continue;
  
  const code = match[1].trim();
  const title = match[2].trim();
  
  // Skip "See industry description for..." entries and very short sector codes
  if (title.startsWith('See industry description')) continue;
  
  entries.push({ c: code, t: title });
}

// Sort by code
entries.sort((a, b) => a.c.localeCompare(b.c));

const output = JSON.stringify(entries);
writeFileSync('C:\\Users\\sergi\\Documents\\GitHub\\corgi\\portal\\src\\data\\naics-codes.json', output);
console.log(`Wrote ${entries.length} NAICS entries`);
