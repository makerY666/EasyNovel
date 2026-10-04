// Stop the development server when its startup terminal closes, including abrupt exit.
import {createRequire} from 'node:module';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
const require=createRequire(resolve('package.json'));
const {createServer}=await import(pathToFileURL(require.resolve('vite')).href);
const port=Number(process.argv[2]);
const parent=Number(process.argv[3]);
if(!Number.isInteger(port)||!Number.isInteger(parent)||parent<=0)throw new Error('Invalid launcher port or parent');
const server=await createServer({server:{host:'127.0.0.1',port,strictPort:true}});
await server.listen();
let closing=false;
const stop=async()=>{if(closing)return;closing=true;clearInterval(timer);await server.close();process.exit(0)};
const timer=setInterval(()=>{try{process.kill(parent,0)}catch{void stop()}},1000);
process.on('SIGINT',()=>void stop());
process.on('SIGTERM',()=>void stop());
