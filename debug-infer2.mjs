import { config as dotenvConfig } from 'dotenv';
import { BlindferenceAgent } from './dist/agent.js';

dotenvConfig();

const agent = new BlindferenceAgent({
  privateKey: process.env.BLF_PRIVATE_KEY,
  paymentServiceUrl: process.env.BLF_PAYMENT_URL,
  iclUrl: process.env.BLF_ICL_URL,
  rpcUrl: process.env.BLF_RPC_URL || process.env.BLF_COFHE_RPC,
});

(async () => {
  try {
    console.log('Address:', agent.getAddress());
    console.log('Step 1: initCofhe...');
    await agent.initCofhe();
    console.log('Step 1 OK');
    
    console.log('Step 2: infer...');
    // Monkey-patch to log the request
    const origPost = agent.paymentClient.post;
    agent.paymentClient.post = async function(...args) {
      console.log('Payment POST:', args[0]);
      console.log('Payload keys:', Object.keys(args[1]));
      return origPost.apply(this, args);
    };
    
    const result = await agent.infer({ prompt: 'test', modelId: 'groq:llama-3.3-70b-versatile' });
    console.log('Result:', result);
  } catch (e) {
    console.error('ERROR:', e.message);
    if (e.response) {
      console.error('Response status:', e.response.status);
      console.error('Response data:', e.response.data);
    }
  }
})();
