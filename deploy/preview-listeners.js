// Executed by Node inside a service container; no host Node installation needed.
// Linux exposes each IPv6 address as four little-endian 32-bit words.
const fs = require('fs');
const requested = Number(process.argv[1] || 0);
const seen = new Set();
for (const [path, ipv6] of [['/proc/net/tcp', false], ['/proc/net/tcp6', true]]) {
    let rows;
    try { rows = fs.readFileSync(path, 'utf8').trim().split('\n').slice(1); }
    catch (error) { if (error.code === 'ENOENT') continue; throw error; }
    for (const row of rows) {
        const fields = row.trim().split(/\s+/);
        if (fields[3] !== '0A') continue;
        const [hex, portHex] = fields[1].split(':');
        const port = parseInt(portHex, 16);
        if (requested && port !== requested) continue;
        let host;
        if (ipv6) {
            const bytes = Buffer.from(hex.match(/.{8}/g).map(word =>
                word.match(/.{2}/g).reverse().join('')).join(''), 'hex');
            const groups = [];
            for (let i = 0; i < 16; i += 2) groups.push(bytes.readUInt16BE(i).toString(16));
            host = '[' + groups.join(':') + ']';
        } else {
            host = Buffer.from(hex, 'hex').reverse().join('.');
        }
        if (host !== '127.0.0.11') seen.add(host + '|' + port);
    }
}
if (requested && seen.size === 0) process.exit(1);
for (const value of seen) process.stdout.write(value + '\n');
