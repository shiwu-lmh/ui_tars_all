import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath, pathToFileURL } from 'node:url';

function argument(name) {
  const index = process.argv.indexOf(name);
  if (index < 0 || index + 1 >= process.argv.length) {
    throw new Error(`Missing argument: ${name}`);
  }
  return process.argv[index + 1];
}

function atomicWrite(file, value) {
  const temporary = `${file}.tmp`;
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
  fs.renameSync(temporary, file);
}

function loadModelSettings(file) {
  const value = JSON.parse(fs.readFileSync(file, 'utf8'));
  if (value.vlmBaseUrl || value.vlmApiKey || value.vlmModelName) {
    return {
      baseURL: value.vlmBaseUrl,
      apiKey: value.vlmApiKey,
      model: value.vlmModelName,
      useResponsesApi: value.useResponsesApi ?? false,
      maxLoopCount: value.maxLoopCount,
      loopIntervalInMs: value.loopIntervalInMs,
    };
  }
  return value;
}

const settingsFile = path.resolve(argument('--settings'));
const promptFile = path.resolve(argument('--prompt-file'));
const statusFile = path.resolve(argument('--status-file'));
const settings = loadModelSettings(settingsFile);
if (!settings.baseURL || !settings.apiKey || !settings.model) {
  throw new Error('VLM settings must include baseURL, apiKey, and model');
}

const projectRoot = path.dirname(fileURLToPath(import.meta.url));
const sdk = await import(pathToFileURL(path.join(projectRoot, 'UI-TARS-desktop-0.3.0/packages/ui-tars/sdk/dist/index.mjs')));
const operatorModule = await import(pathToFileURL(path.join(projectRoot, 'UI-TARS-desktop-0.3.0/packages/ui-tars/operators/nut-js/dist/index.mjs')));
const { GUIAgent } = sdk;
const { NutJSOperator } = operatorModule;

let lastStatus = { status: 'INIT' };
const onData = ({ data }) => {
  lastStatus = {
    status: data.status,
    error: data.error?.message || data.error || null,
    updatedAt: new Date().toISOString(),
  };
  atomicWrite(statusFile, lastStatus);
};

const agent = new GUIAgent({
  model: {
    baseURL: settings.baseURL,
    apiKey: settings.apiKey,
    model: settings.model,
    useResponsesApi: settings.useResponsesApi ?? false,
  },
  operator: new NutJSOperator(),
  maxLoopCount: settings.maxLoopCount,
  loopIntervalInMs: settings.loopIntervalInMs,
  onData,
  onError: ({ error }) => {
    lastStatus = {
      status: 'ERROR',
      error: error?.message || String(error),
      updatedAt: new Date().toISOString(),
    };
    atomicWrite(statusFile, lastStatus);
  },
});

try {
  await agent.run(fs.readFileSync(promptFile, 'utf8'));
} catch (error) {
  lastStatus = {
    status: 'ERROR',
    error: error instanceof Error ? error.message : String(error),
    updatedAt: new Date().toISOString(),
  };
  atomicWrite(statusFile, lastStatus);
}

atomicWrite(statusFile, lastStatus);
if (lastStatus.status === 'END') process.exitCode = 0;
else if (lastStatus.status === 'CALL_USER') process.exitCode = 3;
else process.exitCode = 4;
