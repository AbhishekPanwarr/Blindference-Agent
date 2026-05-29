import { config as dotenvConfig } from 'dotenv';
import { BlindferenceAgent } from './dist/agent.js';

dotenvConfig();

console.log('Env BLF_ICL_URL:', process.env.BLF_ICL_URL);
console.log('Env BLF_PAYMENT_URL:', process.env.BLF_PAYMENT_URL);

const agent = new BlindferenceAgent({
  privateKey: process.env.BLF_PRIVATE_KEY,
  paymentServiceUrl: process.env.BLF_PAYMENT_URL,
  iclUrl: process.env.BLF_ICL_URL,
  rpcUrl: process.env.BLF_RPC_URL || process.env.BLF_COFHE_RPC,
});

(async () => {
  try {
    console.log('Step 1: initCofhe...');
    await agent.initCofhe();
    console.log('Step 1 OK');
    
    console.log('Step 2: infer...');
    const result = await agent.infer({ prompt: 'test', modelId: 'groq:llama-3.3-70b-versatile' });
    console.log('Result:', result);
  } catch (e) {
    console.error('ERROR at step:', e.message);
    console.error(e.stack);
  }
})();
