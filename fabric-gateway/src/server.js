import express from 'express';
import * as grpc from '@grpc/grpc-js';
import { connect, hash, signers } from '@hyperledger/fabric-gateway';
import { createPrivateKey } from 'node:crypto';
import { readFile } from 'node:fs/promises';

const required = ['FABRIC_MSP_ID','FABRIC_CERT_PATH','FABRIC_KEY_PATH','FABRIC_TLS_CERT_PATH','FABRIC_PEER_ENDPOINT','FABRIC_PEER_HOST_ALIAS','FABRIC_CHANNEL','FABRIC_CHAINCODE','GATEWAY_API_TOKEN'];
for (const key of required) if (!process.env[key]) throw new Error(`${key} is required`);
const app = express(); app.use(express.json({limit:'32kb'}));
app.use((req,res,next) => req.get('X-Gateway-Token') === process.env.GATEWAY_API_TOKEN ? next() : res.status(401).json({error:'Unauthorized gateway request.'}));
const timeout = () => ({deadline: Date.now() + Number(process.env.FABRIC_TIMEOUT_MS || 12000)});
function validId(value) { return /^GOV-[A-Z0-9]+-\d{8}-[A-F0-9]{8}$/.test(value || ''); }
function validHash(value) { return /^[a-f0-9]{64}$/.test(value || ''); }
async function contract() {
 const credentials=await readFile(process.env.FABRIC_CERT_PATH); const privateKey=createPrivateKey(await readFile(process.env.FABRIC_KEY_PATH)); const tls=await readFile(process.env.FABRIC_TLS_CERT_PATH);
 const client=new grpc.Client(process.env.FABRIC_PEER_ENDPOINT,grpc.credentials.createSsl(tls),{'grpc.ssl_target_name_override':process.env.FABRIC_PEER_HOST_ALIAS});
 const gateway=connect({client,identity:{mspId:process.env.FABRIC_MSP_ID,credentials},signer:signers.newPrivateKeySigner(privateKey),hash:hash.sha256,evaluateOptions:timeout,endorseOptions:timeout,submitOptions:timeout,commitStatusOptions:timeout});
 return {client,gateway,contract:gateway.getNetwork(process.env.FABRIC_CHANNEL).getContract(process.env.FABRIC_CHAINCODE)};
}
async function invoke(res, fn) { let c; try { c=await contract(); return await fn(c.contract); } catch (error) { console.error(error.name,error.message); if (String(error.message).includes('not found')) return res.status(404).json({error:'Certificate record not found.'}); return res.status(503).json({error:'Fabric service unavailable or transaction failed.'}); } finally { c?.gateway.close(); c?.client.close(); } }
app.get('/health', async (req,res)=>invoke(res,async c=>{await c.evaluateTransaction('Ping'); res.json({ok:true});}));
app.get('/v1/certificates/:id', async (req,res)=> { if(!validId(req.params.id))return res.status(400).json({error:'Invalid document ID.'}); return invoke(res,async c=>{const record=JSON.parse(new TextDecoder().decode(await c.evaluateTransaction('GetCertificate',req.params.id)));res.json({record});});});
app.post('/v1/certificates/register', async (req,res)=> { const {documentId,sha256Hash,certificateType,issuer,issuedAt}=req.body||{}; if(!validId(documentId)||!validHash(sha256Hash)||![certificateType,issuer,issuedAt].every(v=>typeof v==='string'&&v.length<=160))return res.status(400).json({error:'Invalid certificate registration request.'}); return invoke(res,async c=>{try { const existing=JSON.parse(new TextDecoder().decode(await c.evaluateTransaction('GetCertificate',documentId))); return res.status(existing.sha256Hash===sha256Hash?200:409).json({record:existing,reconciled:existing.sha256Hash===sha256Hash}); } catch (error) { if(!String(error.message).includes('not found')) throw error; } const bytes=await c.submitTransaction('RegisterCertificate',documentId,sha256Hash,certificateType,issuer,issuedAt);res.status(201).json({record:JSON.parse(new TextDecoder().decode(bytes))});});});
app.post('/v1/certificates/:id/verify', async (req,res)=> { if(!validId(req.params.id)||!validHash(req.body?.sha256Hash))return res.status(400).json({error:'Invalid verification request.'});return invoke(res,async c=>{const record=JSON.parse(new TextDecoder().decode(await c.evaluateTransaction('VerifyCertificate',req.params.id,req.body.sha256Hash)));res.json({record,hashMatches:record.sha256Hash===req.body.sha256Hash});});});
app.post('/v1/certificates/:id/status', async (req,res)=> {if(!validId(req.params.id)||!['Active','Revoked'].includes(req.body?.status))return res.status(400).json({error:'Invalid status request.'});return invoke(res,async c=>{const args=req.body.status==='Revoked'?[req.params.id]:[req.params.id,req.body.status];const bytes=await c.submitTransaction(req.body.status==='Revoked'?'RevokeCertificate':'UpdateCertificateStatus',...args);res.json({record:JSON.parse(new TextDecoder().decode(bytes))});});});
app.listen(Number(process.env.GATEWAY_PORT||8081),'0.0.0.0',()=>console.log('Fabric gateway listening on localhost'));
