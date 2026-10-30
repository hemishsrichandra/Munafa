const fs=require('node:fs');const crypto=require('node:crypto');const path=require('node:path');
const dist='frontend/dist';
function files(dir){return fs.readdirSync(dir,{withFileTypes:true}).flatMap(f=>f.isDirectory()?files(path.join(dir,f.name)):[path.join(dir,f.name)]);}
const assets=files(dist).filter(f=>!f.endsWith('/sw.js')).map(f=>'/'+path.relative(dist,f).split(path.sep).join('/'));
const version=crypto.createHash('sha256').update(assets.map(a=>fs.readFileSync(dist+a)).join('')).digest('hex').slice(0,16);
const source=fs.readFileSync('frontend/public/sw.js','utf8').replace('__BUILD_VERSION__',version).replace('__SHELL_ASSETS__',JSON.stringify(assets));
fs.writeFileSync(dist+'/sw.js',source);console.log('PWA shell:',assets.length,'public assets; version',version);
